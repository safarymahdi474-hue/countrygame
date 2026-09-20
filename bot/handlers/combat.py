from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.combat import (
    amphibious_target_keyboard,
    confirm_amphibious_keyboard,
    confirm_attack_keyboard,
    occupy_offer_keyboard,
    target_selection_keyboard,
    war_category_keyboard,
)
from bot.keyboards.military import CATEGORY_LABELS, UNIT_LABELS
from bot.models.country import Country
from bot.models.military import UNIT_CATEGORY, UNIT_STATS, CountryUnit, UnitCategory, UnitType
from bot.services import identity, season
from bot.services.combat import AmphibiousError, CombatError, resolve_amphibious_attack, resolve_attack
from bot.services.notify import notify_user
from bot.services.occupation import can_occupy, occupy_country

router = Router(name="combat")


async def _current_country(session: AsyncSession, telegram_user) -> Country | None:
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


@router.callback_query(F.data == "menu:war")
async def on_war_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text("با کدوم دسته حمله می‌کنی؟", reply_markup=war_category_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("acat:"))
async def on_attack_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category = UnitCategory(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    targets = await identity.list_other_countries(
        session, world_id=country.world_id, exclude_country_id=country.id
    )
    if not targets:
        await callback.answer("هیچ کشور دیگه‌ای تو این دنیا نیست.", show_alert=True)
        return

    await callback.message.edit_text(
        f"{CATEGORY_LABELS[category]} — به کدوم کشور حمله می‌کنی؟",
        reply_markup=target_selection_keyboard(category, targets),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("atarget:"))
async def on_attack_target(callback: CallbackQuery, session: AsyncSession) -> None:
    _, category_raw, target_id_raw = callback.data.split(":")
    category = UnitCategory(category_raw)
    target_country_id = int(target_id_raw)

    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country.id)
    )
    attack_order = {
        row.unit_type: row.quantity
        for row in result.scalars().all()
        if UNIT_CATEGORY[row.unit_type] == category and row.quantity > 0
    }
    if not attack_order:
        await callback.answer("هیچ نیرویی از این دسته نداری.", show_alert=True)
        return

    target = await session.execute(select(Country).where(Country.id == target_country_id))
    target_country = target.scalar_one_or_none()
    if target_country is None:
        await callback.answer("این کشور دیگه وجود نداره.", show_alert=True)
        return

    summary = "، ".join(f"{UNIT_LABELS[ut]}×{qty}" for ut, qty in attack_order.items())
    await callback.message.edit_text(
        f"حمله به {target_country.display_name} با: {summary}\n\nمطمئنی؟",
        reply_markup=confirm_attack_keyboard(category, target_country_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aconfirm:"))
async def on_attack_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    _, category_raw, target_id_raw = callback.data.split(":")
    category = UnitCategory(category_raw)
    target_country_id = int(target_id_raw)

    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country.id)
    )
    attack_order = {
        row.unit_type: row.quantity
        for row in result.scalars().all()
        if UNIT_CATEGORY[row.unit_type] == category and row.quantity > 0
    }
    if not attack_order:
        await callback.answer("هیچ نیرویی از این دسته نداری.", show_alert=True)
        return

    try:
        combat_result = await resolve_attack(
            session,
            world_id=country.world_id,
            attacker_country_id=country.id,
            defender_country_id=target_country_id,
            category=category,
            attack_order=attack_order,
        )
    except CombatError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    winner_text = "بردی! 🎉" if combat_result.winner == "attacker" else "باختی 😔"
    lines = [
        winner_text,
        f"قدرت حمله‌کننده: {combat_result.attacker_power:,.0f}",
        f"قدرت مدافع: {combat_result.defender_power:,.0f}",
    ]
    if combat_result.attacker_losses:
        lines.append(
            "تلفات ما: " + "، ".join(f"{UNIT_LABELS[ut]}×{q}" for ut, q in combat_result.attacker_losses.items())
        )
    if combat_result.defender_losses:
        lines.append(
            "تلفات دشمن: " + "، ".join(f"{UNIT_LABELS[ut]}×{q}" for ut, q in combat_result.defender_losses.items())
        )
    if combat_result.money_looted > 0:
        lines.append(f"غارت: ${combat_result.money_looted:,.0f}")

    offer_occupy = (
        combat_result.winner == "attacker"
        and can_occupy(combat_result.attacker_power, combat_result.defender_power)
    )
    if offer_occupy:
        lines.append("\n💡 اختلاف قدرت اونقدر زیاد بود که می‌تونی این کشور رو اشغال کنی:")
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=occupy_offer_keyboard(target_country_id)
        )
    else:
        await callback.message.edit_text("\n".join(lines), reply_markup=war_category_keyboard())
    await callback.answer()

    # به مدافع اطلاع بده که بهش حمله شده
    defender_telegram_id = await identity.get_telegram_id_for_country(session, target_country_id)
    defender_lines = [
        f"🚨 {country.display_name} به تو حمله کرد! ({winner_text})",
        f"قدرت حمله‌کننده: {combat_result.attacker_power:,.0f}",
        f"قدرت دفاع تو: {combat_result.defender_power:,.0f}",
    ]
    if combat_result.defender_losses:
        defender_lines.append(
            "تلفات تو: " + "، ".join(f"{UNIT_LABELS[ut]}×{q}" for ut, q in combat_result.defender_losses.items())
        )
    if combat_result.money_looted > 0:
        defender_lines.append(f"غارت‌شده: ${combat_result.money_looted:,.0f}")
    await notify_user(callback.bot, defender_telegram_id, "\n".join(defender_lines))


@router.callback_query(F.data.startswith("aoccupy:"))
async def on_occupy(callback: CallbackQuery, session: AsyncSession) -> None:
    target_country_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    from bot.services.occupation import OccupationError

    try:
        target = await occupy_country(
            session, occupier_country_id=country.id, target_country_id=target_country_id
        )
    except OccupationError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.message.edit_text(
        f"🏴 {target.display_name} اشغال شد — تولیدش تا {target.occupied_until:%Y-%m-%d %H:%M} نصف می‌مونه.",
        reply_markup=war_category_keyboard(),
    )
    await callback.answer()

    target_telegram_id = await identity.get_telegram_id_for_country(session, target_country_id)
    await notify_user(
        callback.bot, target_telegram_id,
        f"🏴 کشورت توسط {country.display_name} اشغال شد! تولیدت تا آزادسازی نصف می‌مونه.",
    )


@router.callback_query(F.data == "amenu:menu")
async def on_amphibious_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    targets = await identity.list_other_countries(
        session, world_id=country.world_id, exclude_country_id=country.id
    )
    if not targets:
        await callback.answer("هیچ کشور دیگه‌ای تو این دنیا نیست.", show_alert=True)
        return
    await callback.message.edit_text(
        "🚢 کاروان آبی‌خاکی — به کدوم کشور حمله می‌کنی؟",
        reply_markup=amphibious_target_keyboard(targets),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("amtarget:"))
async def on_amphibious_target(callback: CallbackQuery, session: AsyncSession) -> None:
    target_country_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country.id)
    )
    units = {row.unit_type: row.quantity for row in result.scalars().all() if row.quantity > 0}
    transport_qty = units.get(UnitType.TRANSPORT_SHIP, 0)
    ground_units = {ut: qty for ut, qty in units.items() if UNIT_CATEGORY[ut] == UnitCategory.GROUND}

    if transport_qty <= 0:
        await callback.answer("هیچ ناو ترابری نداری.", show_alert=True)
        return
    if not ground_units:
        await callback.answer("هیچ نیروی زمینی‌ای برای اعزام نداری.", show_alert=True)
        return

    target = await session.execute(select(Country).where(Country.id == target_country_id))
    target_country = target.scalar_one_or_none()
    if target_country is None:
        await callback.answer("این کشور دیگه وجود نداره.", show_alert=True)
        return

    summary = "، ".join(f"{UNIT_LABELS[ut]}×{qty}" for ut, qty in ground_units.items())
    await callback.message.edit_text(
        f"اعزام به {target_country.display_name} با {transport_qty} ناو ترابری، حامل: {summary}\n\nمطمئنی؟",
        reply_markup=confirm_amphibious_keyboard(target_country_id, transport_qty),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("amconfirm:"))
async def on_amphibious_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    _, target_id_raw, transport_qty_raw = callback.data.split(":")
    target_country_id = int(target_id_raw)
    transport_qty = int(transport_qty_raw)

    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country.id)
    )
    units = {row.unit_type: row.quantity for row in result.scalars().all() if row.quantity > 0}
    ground_units = {ut: qty for ut, qty in units.items() if UNIT_CATEGORY[ut] == UnitCategory.GROUND}

    try:
        combat_result = await resolve_amphibious_attack(
            session,
            world_id=country.world_id,
            attacker_country_id=country.id,
            defender_country_id=target_country_id,
            transport_ship_quantity=transport_qty,
            ground_attack_order=ground_units,
        )
    except AmphibiousError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    winner_text = "بردی! 🎉" if combat_result.winner == "attacker" else "باختی 😔"
    lines = [
        f"🚢 نتیجه‌ی کاروان آبی‌خاکی: {winner_text}",
        f"قدرت حمله‌کننده: {combat_result.attacker_power:,.0f}",
        f"قدرت مدافع: {combat_result.defender_power:,.0f}",
    ]
    if combat_result.attacker_losses:
        lines.append(
            "تلفات ما: " + "، ".join(f"{UNIT_LABELS[ut]}×{q}" for ut, q in combat_result.attacker_losses.items())
        )
    if combat_result.defender_losses:
        lines.append(
            "تلفات دشمن: " + "، ".join(f"{UNIT_LABELS[ut]}×{q}" for ut, q in combat_result.defender_losses.items())
        )
    if combat_result.money_looted > 0:
        lines.append(f"غارت: ${combat_result.money_looted:,.0f}")

    await callback.message.edit_text("\n".join(lines), reply_markup=war_category_keyboard())
    await callback.answer()

    defender_telegram_id = await identity.get_telegram_id_for_country(session, target_country_id)
    await notify_user(
        callback.bot, defender_telegram_id,
        f"🚢 {country.display_name} با کاروان آبی‌خاکی بهت حمله کرد! ({winner_text})",
    )
