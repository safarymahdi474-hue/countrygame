"""
فرمول‌های اقتصادی — نسخه‌ی خودمون، جدا از هر بازی دیگه.

منطق: تولید هر ساختمان به‌صورت پلکانی-تصاعدی رشد می‌کنه (نه خطی صرف)
تا ساختن سطح‌های بالاتر واقعاً حس ارتقا بده، ولی سقف داره که تعادل
اقتصادی به‌هم نخوره.

فرمول پایه:
    output(level) = base_output * (growth_factor ** (level - 1))  برای level >= 1
    output(0) = 0

هر نوع ساختمان base_output و growth_factor خودش رو داره.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bot.models.buildings import BuildingType
from bot.models.country import CountryTier

GROWTH_FACTOR = Decimal("1.35")  # هر سطح ~۳۵٪ بیشتر از سطح قبل تولید می‌کنه


@dataclass(frozen=True, slots=True)
class BuildingEconomics:
    base_output: Decimal       # تولید در سطح ۱ (واحد در روز) — برای ساختمان‌های تولیدمنبع
    base_upgrade_cost: Decimal  # هزینه‌ی پول برای رسیدن از سطح ۰ به ۱
    cost_growth_factor: Decimal = Decimal("1.8")  # هر سطح چقدر گرون‌تر می‌شه
    power_consumption: int = 5  # مصرف برق ثابت (فعلاً ساده، صرف‌نظر از سطح)
    capacity_per_level: int = 0  # برای ساختمان‌های ظرفیت‌ساز نظامی (پادگان/فرودگاه/بندر/سیلو)
    welfare_bonus_per_level: Decimal = Decimal("0")  # درصد بونس درآمد کل کشور، هر سطح
    radar_reduction_per_level: Decimal = Decimal("0")  # کاهش دقتِ موشکِ دشمن، هر سطح
    lab_discount_per_level: Decimal = Decimal("0")  # تخفیف هزینه‌ی ساخت یگان، هر سطح


BUILDING_ECONOMICS: dict[BuildingType, BuildingEconomics] = {
    BuildingType.STEEL_MINE: BuildingEconomics(
        base_output=Decimal("30000"), base_upgrade_cost=Decimal("650000")
    ),
    BuildingType.URANIUM_MINE: BuildingEconomics(
        base_output=Decimal("60000"), base_upgrade_cost=Decimal("1300000")
    ),
    BuildingType.OIL_WELL: BuildingEconomics(
        base_output=Decimal("350000"), base_upgrade_cost=Decimal("2800000")
    ),
    BuildingType.REFINERY: BuildingEconomics(
        base_output=Decimal("500000"), base_upgrade_cost=Decimal("3900000")
    ),
    BuildingType.STEEL_INDUSTRY: BuildingEconomics(
        base_output=Decimal("50000"), base_upgrade_cost=Decimal("1400000")
    ),
    BuildingType.WIND_PLANT: BuildingEconomics(
        base_output=Decimal("35"), base_upgrade_cost=Decimal("1300000"), power_consumption=0
    ),
    BuildingType.SOLAR_PLANT: BuildingEconomics(
        base_output=Decimal("50"), base_upgrade_cost=Decimal("2000000"), power_consumption=0
    ),
    BuildingType.HYDRO_PLANT: BuildingEconomics(
        base_output=Decimal("70"), base_upgrade_cost=Decimal("1500000"), power_consumption=0
    ),
    BuildingType.NUCLEAR_PLANT: BuildingEconomics(
        base_output=Decimal("90"), base_upgrade_cost=Decimal("2400000"), power_consumption=0
    ),
    BuildingType.FARM: BuildingEconomics(
        base_output=Decimal("1200000"), base_upgrade_cost=Decimal("6800000")
    ),
    BuildingType.RANCH: BuildingEconomics(
        base_output=Decimal("800000"), base_upgrade_cost=Decimal("6800000")
    ),
    # --- رفاه: بونس درصدی درآمد، سقف کلی رو تابع welfare_income_multiplier اعمال می‌کنه ---
    BuildingType.HOSPITAL: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1200000"),
        welfare_bonus_per_level=Decimal("0.009"),
    ),
    BuildingType.POLICE_STATION: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("900000"),
        welfare_bonus_per_level=Decimal("0.015"),
    ),
    BuildingType.UNIVERSITY: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1000000"),
        welfare_bonus_per_level=Decimal("0.016"),
    ),
    # --- نظامی: ظرفیت‌ساز — base_output استفاده نمی‌شه، capacity_per_level مهمه ---
    BuildingType.GARRISON: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("800000"), capacity_per_level=40
    ),
    BuildingType.AIRPORT: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("2000000"), capacity_per_level=15
    ),
    BuildingType.PORT: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1800000"), capacity_per_level=15
    ),
    BuildingType.MISSILE_SILO: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1800000"), capacity_per_level=8
    ),
    # --- نظامی: کارخانه — صرفاً امکان ساخت رو باز می‌کنن، سطح‌شون سرعت ساخت رو زیاد می‌کنه ---
    BuildingType.TANK_FACTORY: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("800000")
    ),
    BuildingType.AIRCRAFT_FACTORY: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1500000")
    ),
    BuildingType.SHIPYARD: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1800000")
    ),
    BuildingType.MISSILE_FACTORY: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("2000000")
    ),
    BuildingType.COMMAND_HQ: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("1200000")
    ),
    # --- استراتژیک ---
    BuildingType.RADAR: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("700000"),
        radar_reduction_per_level=Decimal("0.04"),  # هر سطح ۴٪ از دقت موشک دشمن کم می‌کنه
    ),
    BuildingType.LAB: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("2500000"),
        lab_discount_per_level=Decimal("0.03"),  # هر سطح ۳٪ تخفیف هزینه‌ی ساخت یگان
    ),
    BuildingType.SPACE_CENTER: BuildingEconomics(
        base_output=Decimal("0"), base_upgrade_cost=Decimal("6000000"),
    ),
}


LAB_DISCOUNT_CAP = Decimal("0.5")   # حداکثر ۵۰٪ تخفیف کلی، هرچقدر هم آزمایشگاه ارتقا بدی
RADAR_REDUCTION_CAP = Decimal("0.6")  # حداکثر ۶۰٪ کاهش دقت موشک دشمن


def radar_missile_reduction(level: int) -> Decimal:
    if level <= 0:
        return Decimal("0")
    econ = BUILDING_ECONOMICS[BuildingType.RADAR]
    return min(econ.radar_reduction_per_level * level, RADAR_REDUCTION_CAP)


def lab_unit_cost_discount(level: int) -> Decimal:
    if level <= 0:
        return Decimal("0")
    econ = BUILDING_ECONOMICS[BuildingType.LAB]
    return min(econ.lab_discount_per_level * level, LAB_DISCOUNT_CAP)


def capacity_at_level(building_type: BuildingType, level: int) -> int:
    """ظرفیت (تعداد یگان قابل‌نگهداری) یک ساختمان ظرفیت‌ساز در سطح مشخص."""
    if level <= 0:
        return 0
    econ = BUILDING_ECONOMICS[building_type]
    return econ.capacity_per_level * level


def daily_output(building_type: BuildingType, level: int) -> Decimal:
    """تولید روزانه‌ی یک ساختمان در سطح مشخص."""
    if level <= 0:
        return Decimal("0")
    econ = BUILDING_ECONOMICS[building_type]
    return econ.base_output * (GROWTH_FACTOR ** (level - 1))


def upgrade_cost(building_type: BuildingType, target_level: int) -> Decimal:
    """هزینه‌ی پولی ارتقا به یک سطح مشخص (از سطح target_level - 1)."""
    if target_level <= 0:
        return Decimal("0")
    econ = BUILDING_ECONOMICS[building_type]
    return econ.base_upgrade_cost * (econ.cost_growth_factor ** (target_level - 1))


WELFARE_BONUS_CAP = Decimal("0.5")  # حداکثر ۵۰٪ بونس کل، هرچقدر هم رفاه بسازی


def welfare_bonus_fraction(building_type: BuildingType, level: int) -> Decimal:
    """بونس درصدی یک ساختمان رفاهی در سطح مشخص (بدون اعمال سقف کلی)."""
    if level <= 0:
        return Decimal("0")
    econ = BUILDING_ECONOMICS[building_type]
    return econ.welfare_bonus_per_level * level


# --- خزانه‌ی شروع بر اساس تیر کشور — عمداً متفاوت از هر بازی دیگه ---
STARTING_TREASURY: dict[CountryTier, Decimal] = {
    CountryTier.STANDARD: Decimal("8000000"),
    CountryTier.ADVANCED: Decimal("11000000"),
    CountryTier.ELITE: Decimal("14000000"),
}
