from __future__ import annotations

import enum

import datetime as dt

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base
from bot.models.resources import ResourceType


class BuildingCategory(str, enum.Enum):
    RESOURCE = "resource"      # معدن/چاه/کارخانه استخراج
    POWER = "power"            # نیروگاه
    FOOD = "food"               # کشاورزی/دامداری
    WELFARE = "welfare"         # رفاه (بیمارستان، دانشگاه ...)
    MILITARY = "military"       # پادگان/فرودگاه/بندر (فاز نظامی کاملش می‌کنیم)
    STRATEGIC = "strategic"     # رادار، آزمایشگاه، مرکز فضایی


class BuildingType(str, enum.Enum):
    # --- منابع ---
    STEEL_MINE = "steel_mine"
    URANIUM_MINE = "uranium_mine"
    OIL_WELL = "oil_well"
    REFINERY = "refinery"
    STEEL_INDUSTRY = "steel_industry"
    # --- برق ---
    WIND_PLANT = "wind_plant"
    SOLAR_PLANT = "solar_plant"
    HYDRO_PLANT = "hydro_plant"
    NUCLEAR_PLANT = "nuclear_plant"
    # --- غذا ---
    FARM = "farm"
    RANCH = "ranch"
    # --- رفاه (بونس درصدی به کل درآمد کشور) ---
    HOSPITAL = "hospital"
    POLICE_STATION = "police_station"
    UNIVERSITY = "university"
    # --- نظامی: ظرفیت‌ساز ---
    GARRISON = "garrison"          # ظرفیت نیروی زمینی
    AIRPORT = "airport"            # ظرفیت نیروی هوایی
    PORT = "port"                  # ظرفیت نیروی دریایی
    MISSILE_SILO = "missile_silo"  # ظرفیت موشک
    # --- نظامی: کارخانه‌ساز ---
    TANK_FACTORY = "tank_factory"
    AIRCRAFT_FACTORY = "aircraft_factory"
    SHIPYARD = "shipyard"
    MISSILE_FACTORY = "missile_factory"
    COMMAND_HQ = "command_hq"      # ستاد فرماندهی — بونس دفاعی کل کشور
    # --- استراتژیک ---
    RADAR = "radar"                # کاهش دقت موشکِ دشمن روی خاکت
    LAB = "lab"                    # تخفیف هزینه‌ی ساخت یگان (تحقیقات)
    SPACE_CENTER = "space_center"  # امکان شناسایی (دیدن آمار نظامی کشور هدف قبل از حمله)


# نگاشت هر نوع ساختمان به دسته و منبعی که تولید می‌کنه
BUILDING_CATEGORY: dict[BuildingType, BuildingCategory] = {
    BuildingType.STEEL_MINE: BuildingCategory.RESOURCE,
    BuildingType.URANIUM_MINE: BuildingCategory.RESOURCE,
    BuildingType.OIL_WELL: BuildingCategory.RESOURCE,
    BuildingType.REFINERY: BuildingCategory.RESOURCE,
    BuildingType.STEEL_INDUSTRY: BuildingCategory.RESOURCE,
    BuildingType.WIND_PLANT: BuildingCategory.POWER,
    BuildingType.SOLAR_PLANT: BuildingCategory.POWER,
    BuildingType.HYDRO_PLANT: BuildingCategory.POWER,
    BuildingType.NUCLEAR_PLANT: BuildingCategory.POWER,
    BuildingType.FARM: BuildingCategory.FOOD,
    BuildingType.RANCH: BuildingCategory.FOOD,
    BuildingType.HOSPITAL: BuildingCategory.WELFARE,
    BuildingType.POLICE_STATION: BuildingCategory.WELFARE,
    BuildingType.UNIVERSITY: BuildingCategory.WELFARE,
    BuildingType.GARRISON: BuildingCategory.MILITARY,
    BuildingType.AIRPORT: BuildingCategory.MILITARY,
    BuildingType.PORT: BuildingCategory.MILITARY,
    BuildingType.MISSILE_SILO: BuildingCategory.MILITARY,
    BuildingType.TANK_FACTORY: BuildingCategory.MILITARY,
    BuildingType.AIRCRAFT_FACTORY: BuildingCategory.MILITARY,
    BuildingType.SHIPYARD: BuildingCategory.MILITARY,
    BuildingType.MISSILE_FACTORY: BuildingCategory.MILITARY,
    BuildingType.COMMAND_HQ: BuildingCategory.MILITARY,
    BuildingType.RADAR: BuildingCategory.STRATEGIC,
    BuildingType.LAB: BuildingCategory.STRATEGIC,
    BuildingType.SPACE_CENTER: BuildingCategory.STRATEGIC,
}

BUILDING_OUTPUT_RESOURCE: dict[BuildingType, ResourceType | None] = {
    BuildingType.STEEL_MINE: ResourceType.STEEL,
    BuildingType.URANIUM_MINE: ResourceType.URANIUM,
    BuildingType.OIL_WELL: ResourceType.OIL,
    BuildingType.REFINERY: ResourceType.OIL,
    BuildingType.STEEL_INDUSTRY: ResourceType.STEEL,
    BuildingType.WIND_PLANT: ResourceType.POWER,
    BuildingType.SOLAR_PLANT: ResourceType.POWER,
    BuildingType.HYDRO_PLANT: ResourceType.POWER,
    BuildingType.NUCLEAR_PLANT: ResourceType.POWER,
    BuildingType.FARM: ResourceType.FOOD,
    BuildingType.RANCH: ResourceType.FOOD,
    BuildingType.HOSPITAL: None,
    BuildingType.POLICE_STATION: None,
    BuildingType.UNIVERSITY: None,
    # ساختمان‌های نظامی منبع تولید نمی‌کنن — ظرفیت یا امکان ساخت می‌دن
    BuildingType.GARRISON: None,
    BuildingType.AIRPORT: None,
    BuildingType.PORT: None,
    BuildingType.MISSILE_SILO: None,
    BuildingType.TANK_FACTORY: None,
    BuildingType.AIRCRAFT_FACTORY: None,
    BuildingType.SHIPYARD: None,
    BuildingType.MISSILE_FACTORY: None,
    BuildingType.COMMAND_HQ: None,
    BuildingType.RADAR: None,
    BuildingType.LAB: None,
    BuildingType.SPACE_CENTER: None,
}

MAX_BUILDING_LEVEL = 5


class CountryBuilding(Base):
    """یک نوع ساختمان که یک کشور ساخته (یا در حال ساخت داره)، با سطح فعلی‌ش."""

    __tablename__ = "country_buildings"
    __table_args__ = (
        UniqueConstraint("country_id", "building_type", name="uq_country_building"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    building_type: Mapped[BuildingType] = mapped_column(
        Enum(BuildingType, native_enum=False)
    )
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0 یعنی هنوز ساخته نشده

    # اگه در حال ساخت/ارتقا باشه، این فیلد پر می‌شه؛ تایمر فاز بعد این رو چک می‌کنه
    upgrade_finishes_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
