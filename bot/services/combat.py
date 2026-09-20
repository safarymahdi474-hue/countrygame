"""
موتور نبرد — طراحی خودمون، جدا از هر بازی دیگه.

خلاصه‌ی منطق:
1. حمله‌کننده تعدادی یگان از یک دسته (زمینی/هوایی/دریایی/موشکی) می‌فرسته.
2. همه‌ی یگان‌های همون دسته که مدافع داره، خودکار دفاع می‌کنن
   (فعلاً امکان «نگه‌داشتن بخشی از نیرو در پشت جبهه» نداریم — فاز بعد اضافه می‌شه).
3. قدرت هر طرف = مجموع (attack × تعداد × دقت) با کمی نوسان تصادفی.
4. بونس ستاد فرماندهی (COMMAND_HQ): هر سطح ۱۰٪ به قدرت دفاعی مدافع اضافه می‌کنه.
5. تلفات هر طرف متناسب با قدرت طرف مقابله؛ evasion یگان تلفاتش رو کم می‌کنه.
6. اگه حمله‌کننده ببره، درصدی از خزانه‌ی مدافع غارت می‌شه (متناسب با اختلاف قدرت).

این یه شبیه‌سازی احتمالاتی‌ـ‌تعیینی ترکیبیه: نوسان تصادفی هست ولی نتیجه
کاملاً شانسی نیست — کشوری که یگان و فرمانده‌ی بهتری داره، به‌طور میانگین برنده‌ست.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BuildingType, CountryBuilding
from bot.models.combat import CombatReport
from bot.models.country import Country
from bot.models.military import UNIT_CATEGORY, UNIT_STATS, CountryUnit, UnitCategory, UnitType
from bot.services import ledger
from bot.services.economy import radar_missile_reduction

BASE_LOSS_FACTOR = Decimal("0.35")   # حداکثر کسری از نیروی درگیر که در یک نبرد از دست می‌ره
HQ_DEFENSE_BONUS_PER_LEVEL = Decimal("0.10")  # هر سطح ستاد فرماندهی = ۱۰٪ دفاع بیشتر
LOOT_BASE_RATE = Decimal("0.05")     # حداقل درصد غارت در صورت برد قاطع
LOOT_MAX_RATE = Decimal("0.15")      # حداکثر درصد غارت


class CombatError(Exception):
    pass


@dataclass
class CombatResult:
    winner: str  # "attacker" | "defender"
    attacker_power: Decimal
    defender_power: Decimal
    attacker_losses: dict[UnitType, int] = field(default_factory=dict)
    defender_losses: dict[UnitType, int] = field(default_factory=dict)
    money_looted: Decimal = Decimal("0")


async def _country_units_by_type(
    session: AsyncSession, country_id: int
) -> dict[UnitType, CountryUnit]:
    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country_id)
    )
    return {row.unit_type: row for row in result.scalars().all()}


async def _hq_level(session: AsyncSession, country_id: int) -> int:
    result = await session.execute(
        select(CountryBuilding.level).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.building_type == BuildingType.COMMAND_HQ,
        )
    )
    return result.scalar_one_or_none() or 0


async def _radar_level(session: AsyncSession, country_id: int) -> int:
    result = await session.execute(
        select(CountryBuilding.level).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.building_type == BuildingType.RADAR,
        )
    )
    return result.scalar_one_or_none() or 0


def _rolled_power(
    units: dict[UnitType, int], *, is_attack: bool, rng: random.Random
) -> Decimal:
    """
    قدرت یک طرف رو حساب می‌کنه: attack * تعداد * (دقت/۱۰۰) * نوسان تصادفی.
    برای دفاع از evasion به‌جای accuracy استفاده نمی‌کنیم اینجا —
    evasion جدا روی تلفاتِ *خودِ* اون یگان اثر می‌ذاره، نه روی قدرت حمله‌اش.
    """
    total = Decimal("0")
    for unit_type, quantity in units.items():
        if quantity <= 0:
            continue
        stats = UNIT_STATS[unit_type]
        variance = Decimal(str(round(rng.uniform(0.85, 1.15), 4)))
        total += Decimal(stats.attack) * Decimal(quantity) * (Decimal(stats.accuracy) / 100) * variance
    return total


def _apply_losses(
    units: dict[UnitType, int], loss_fraction: Decimal, rng: random.Random
) -> dict[UnitType, int]:
    losses: dict[UnitType, int] = {}
    for unit_type, quantity in units.items():
        if quantity <= 0:
            continue
        stats = UNIT_STATS[unit_type]
        evasion_reduction = Decimal(stats.evasion) / 100
        effective_fraction = loss_fraction * (Decimal("1") - evasion_reduction)
        effective_fraction = max(Decimal("0"), min(effective_fraction, Decimal("1")))
        # کمی نوسان روی تلفات هم می‌ذاریم که هر نبرد عین قبلی نباشه
        noise = Decimal(str(round(rng.uniform(0.9, 1.1), 4)))
        lost = int((Decimal(quantity) * effective_fraction * noise).to_integral_value())
        lost = max(0, min(lost, quantity))
        if lost > 0:
            losses[unit_type] = lost
    return losses


async def resolve_attack(
    session: AsyncSession,
    *,
    world_id: int,
    attacker_country_id: int,
    defender_country_id: int,
    category: UnitCategory,
    attack_order: dict[UnitType, int],
    rng: random.Random | None = None,
) -> CombatResult:
    """
    یک حمله رو از ابتدا تا انتها اجرا می‌کنه: اعتبارسنجی، محاسبه، اعمال تلفات
    و غارت، و ثبت گزارش. باید داخل session_scope صدا زده بشه.
    """
    rng = rng or random.Random()

    if attacker_country_id == defender_country_id:
        raise CombatError("نمی‌تونی به خودت حمله کنی.")

    for unit_type in attack_order:
        if UNIT_CATEGORY[unit_type] != category:
            raise CombatError(f"{unit_type.value} متعلق به دسته‌ی {category.value} نیست.")

    attacker_units = await _country_units_by_type(session, attacker_country_id)
    for unit_type, requested in attack_order.items():
        available = attacker_units.get(unit_type)
        available_qty = available.quantity if available else 0
        if requested > available_qty:
            raise CombatError(
                f"تعداد {unit_type.value} کافی نیست ({available_qty} موجود، {requested} درخواستی)."
            )

    defender_units_all = await _country_units_by_type(session, defender_country_id)
    defending_units = {
        ut: row.quantity
        for ut, row in defender_units_all.items()
        if UNIT_CATEGORY[ut] == category and row.quantity > 0
    }

    attacker_power = _rolled_power(attack_order, is_attack=True, rng=rng)

    if category == UnitCategory.MISSILE:
        radar_level = await _radar_level(session, defender_country_id)
        reduction = radar_missile_reduction(radar_level)
        if reduction > 0:
            attacker_power *= Decimal("1") - reduction

    defender_power = _rolled_power(defending_units, is_attack=False, rng=rng)
    hq_level = await _hq_level(session, defender_country_id)
    defender_power *= Decimal("1") + (HQ_DEFENSE_BONUS_PER_LEVEL * hq_level)

    total_power = attacker_power + defender_power
    if total_power <= 0:
        raise CombatError("هیچ نیرویی برای نبرد وجود نداره.")

    attacker_loss_fraction = (defender_power / total_power) * BASE_LOSS_FACTOR
    defender_loss_fraction = (attacker_power / total_power) * BASE_LOSS_FACTOR

    attacker_losses = _apply_losses(attack_order, attacker_loss_fraction, rng)
    defender_losses = _apply_losses(defending_units, defender_loss_fraction, rng)

    winner = "attacker" if attacker_power > defender_power else "defender"

    # --- اعمال تلفات روی دیتابیس ---
    for unit_type, lost in attacker_losses.items():
        attacker_units[unit_type].quantity -= lost
    for unit_type, lost in defender_losses.items():
        defender_units_all[unit_type].quantity -= lost

    # --- غارت، فقط در صورت برد قاطع حمله‌کننده ---
    money_looted = Decimal("0")
    if winner == "attacker" and total_power > 0:
        margin = (attacker_power - defender_power) / total_power  # بین 0 و 1
        loot_rate = LOOT_BASE_RATE + (LOOT_MAX_RATE - LOOT_BASE_RATE) * max(Decimal("0"), margin)
        defender_result = await session.execute(
            select(Country).where(Country.id == defender_country_id)
        )
        defender_country = defender_result.scalar_one()
        money_looted = (defender_country.treasury * loot_rate).quantize(Decimal("0.01"))
        defender_country.treasury -= money_looted
        await ledger.record_entry(
            session, country_id=defender_country_id, item=None, delta=-money_looted,
            source="combat:looted",
        )

        attacker_result = await session.execute(
            select(Country).where(Country.id == attacker_country_id)
        )
        attacker_country = attacker_result.scalar_one()
        attacker_country.treasury += money_looted
        await ledger.record_entry(
            session, country_id=attacker_country_id, item=None, delta=money_looted,
            source="combat:loot",
        )

    # --- ثبت گزارش ---
    def summarize(losses: dict[UnitType, int]) -> str:
        return ", ".join(f"{ut.value}:-{qty}" for ut, qty in losses.items()) or "بدون تلفات"

    report = CombatReport(
        world_id=world_id,
        attacker_country_id=attacker_country_id,
        defender_country_id=defender_country_id,
        category=category.value,
        winner=winner,
        attacker_power=attacker_power.quantize(Decimal("0.01")),
        defender_power=defender_power.quantize(Decimal("0.01")),
        attacker_losses_summary=summarize(attacker_losses),
        defender_losses_summary=summarize(defender_losses),
        money_looted=money_looted,
    )
    session.add(report)

    return CombatResult(
        winner=winner,
        attacker_power=attacker_power,
        defender_power=defender_power,
        attacker_losses=attacker_losses,
        defender_losses=defender_losses,
        money_looted=money_looted,
    )


class AmphibiousError(Exception):
    pass


async def resolve_amphibious_attack(
    session: AsyncSession,
    *,
    world_id: int,
    attacker_country_id: int,
    defender_country_id: int,
    transport_ship_quantity: int,
    ground_attack_order: dict[UnitType, int],
    rng: random.Random | None = None,
) -> CombatResult:
    """
    حمله‌ی آبی‌خاکی: نیروی زمینی رو با ناو ترابری به یه کشور دیگه (حتی
    بدون مرز مشترک) می‌بری و اونجا با نیروی زمینیِ مدافع می‌جنگی.
    ساده‌سازی نسبت به لجستیک واقعی: فعلاً نبرد دریایی جدا برای غرق‌کردنِ
    ناوها قبل از پیاده‌شدن نداریم؛ فقط چک می‌کنیم ظرفیت حملِ ترابری کافی باشه.
    """
    rng = rng or random.Random()

    if transport_ship_quantity <= 0:
        raise AmphibiousError("باید حداقل یه ناو ترابری بفرستی.")
    if not ground_attack_order:
        raise AmphibiousError("باید حداقل یه یگان زمینی بفرستی.")
    for unit_type in ground_attack_order:
        if UNIT_CATEGORY[unit_type] != UnitCategory.GROUND:
            raise AmphibiousError(f"{unit_type.value} یگان زمینی نیست.")

    attacker_units = await _country_units_by_type(session, attacker_country_id)
    transport_row = attacker_units.get(UnitType.TRANSPORT_SHIP)
    available_transports = transport_row.quantity if transport_row else 0
    if transport_ship_quantity > available_transports:
        raise AmphibiousError(
            f"ناو ترابری کافی نیست ({available_transports} موجود، {transport_ship_quantity} درخواستی)."
        )

    cargo_per_ship = UNIT_STATS[UnitType.TRANSPORT_SHIP].cargo_capacity
    total_cargo_capacity = cargo_per_ship * transport_ship_quantity
    needed_cargo = sum(
        UNIT_STATS[ut].capacity_slots * qty for ut, qty in ground_attack_order.items()
    )
    if needed_cargo > total_cargo_capacity:
        raise AmphibiousError(
            f"ظرفیت حمل کافی نیست: {total_cargo_capacity} جا داری، {needed_cargo} لازمه "
            f"(هر ناو {cargo_per_ship} جا داره)."
        )

    for unit_type, requested in ground_attack_order.items():
        available = attacker_units.get(unit_type)
        available_qty = available.quantity if available else 0
        if requested > available_qty:
            raise AmphibiousError(
                f"تعداد {unit_type.value} کافی نیست ({available_qty} موجود، {requested} درخواستی)."
            )

    return await resolve_attack(
        session,
        world_id=world_id,
        attacker_country_id=attacker_country_id,
        defender_country_id=defender_country_id,
        category=UnitCategory.GROUND,
        attack_order=ground_attack_order,
        rng=rng,
    )
