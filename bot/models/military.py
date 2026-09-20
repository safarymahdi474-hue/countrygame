from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum

from bot.database.engine import Base
from bot.models.buildings import BuildingType
from bot.models.resources import ResourceType


class UnitCategory(str, enum.Enum):
    GROUND = "ground"
    AIR = "air"
    NAVAL = "naval"
    MISSILE = "missile"


class UnitType(str, enum.Enum):
    # زمینی
    INFANTRY = "infantry"
    TANK = "tank"
    ARTILLERY = "artillery"
    # هوایی
    FIGHTER = "fighter"
    BOMBER = "bomber"
    TRANSPORT_PLANE = "transport_plane"
    # دریایی
    DESTROYER = "destroyer"
    SUBMARINE = "submarine"
    CARRIER = "carrier"
    TRANSPORT_SHIP = "transport_ship"
    # موشکی
    SHORT_RANGE_MISSILE = "short_range_missile"
    LONG_RANGE_MISSILE = "long_range_missile"
    AIR_DEFENSE = "air_defense"


UNIT_CATEGORY: dict[UnitType, UnitCategory] = {
    UnitType.INFANTRY: UnitCategory.GROUND,
    UnitType.TANK: UnitCategory.GROUND,
    UnitType.ARTILLERY: UnitCategory.GROUND,
    UnitType.FIGHTER: UnitCategory.AIR,
    UnitType.BOMBER: UnitCategory.AIR,
    UnitType.TRANSPORT_PLANE: UnitCategory.AIR,
    UnitType.DESTROYER: UnitCategory.NAVAL,
    UnitType.SUBMARINE: UnitCategory.NAVAL,
    UnitType.CARRIER: UnitCategory.NAVAL,
    UnitType.TRANSPORT_SHIP: UnitCategory.NAVAL,
    UnitType.SHORT_RANGE_MISSILE: UnitCategory.MISSILE,
    UnitType.LONG_RANGE_MISSILE: UnitCategory.MISSILE,
    UnitType.AIR_DEFENSE: UnitCategory.MISSILE,
}

# کدوم کارخانه این یگان رو می‌سازه
UNIT_FACTORY: dict[UnitType, BuildingType] = {
    UnitType.INFANTRY: BuildingType.GARRISON,       # پیاده‌نظام نیاز به کارخونه‌ی جدا نداره
    UnitType.TANK: BuildingType.TANK_FACTORY,
    UnitType.ARTILLERY: BuildingType.TANK_FACTORY,
    UnitType.FIGHTER: BuildingType.AIRCRAFT_FACTORY,
    UnitType.BOMBER: BuildingType.AIRCRAFT_FACTORY,
    UnitType.TRANSPORT_PLANE: BuildingType.AIRCRAFT_FACTORY,
    UnitType.DESTROYER: BuildingType.SHIPYARD,
    UnitType.SUBMARINE: BuildingType.SHIPYARD,
    UnitType.CARRIER: BuildingType.SHIPYARD,
    UnitType.TRANSPORT_SHIP: BuildingType.SHIPYARD,
    UnitType.SHORT_RANGE_MISSILE: BuildingType.MISSILE_FACTORY,
    UnitType.LONG_RANGE_MISSILE: BuildingType.MISSILE_FACTORY,
    UnitType.AIR_DEFENSE: BuildingType.MISSILE_FACTORY,
}

# کدوم ظرفیت‌ساز جا می‌گیره
UNIT_CAPACITY_BUILDING: dict[UnitType, BuildingType] = {
    UnitType.INFANTRY: BuildingType.GARRISON,
    UnitType.TANK: BuildingType.GARRISON,
    UnitType.ARTILLERY: BuildingType.GARRISON,
    UnitType.FIGHTER: BuildingType.AIRPORT,
    UnitType.BOMBER: BuildingType.AIRPORT,
    UnitType.TRANSPORT_PLANE: BuildingType.AIRPORT,
    UnitType.DESTROYER: BuildingType.PORT,
    UnitType.SUBMARINE: BuildingType.PORT,
    UnitType.CARRIER: BuildingType.PORT,
    UnitType.TRANSPORT_SHIP: BuildingType.PORT,
    UnitType.SHORT_RANGE_MISSILE: BuildingType.MISSILE_SILO,
    UnitType.LONG_RANGE_MISSILE: BuildingType.MISSILE_SILO,
    UnitType.AIR_DEFENSE: BuildingType.MISSILE_SILO,
}


@dataclass(frozen=True, slots=True)
class UnitStats:
    build_cost_money: Decimal
    build_cost_resources: dict[ResourceType, Decimal] = field(default_factory=dict)
    upkeep_money_per_day: Decimal = Decimal("0")
    upkeep_resources_per_day: dict[ResourceType, Decimal] = field(default_factory=dict)
    capacity_slots: int = 1        # چند اسلات از ظرفیت‌ساز مربوطه مصرف می‌کنه
    cargo_capacity: int = 0        # فقط برای ترابری: چند اسلاتِ نیروی زمینی می‌تونه حمل کنه
    attack: int = 0                # قدرت حمله خام
    accuracy: int = 85             # درصد اصابت
    evasion: int = 5               # درصد فرار/جاخالی در برابر حمله
    dmg_vs_ground: int = 0
    dmg_vs_air: int = 0
    dmg_vs_naval: int = 0


UNIT_STATS: dict[UnitType, UnitStats] = {
    UnitType.INFANTRY: UnitStats(
        build_cost_money=Decimal("8000"),
        build_cost_resources={ResourceType.STEEL: Decimal("10")},
        upkeep_money_per_day=Decimal("7"),
        upkeep_resources_per_day={ResourceType.FOOD: Decimal("1728")},
        capacity_slots=1, attack=5, accuracy=85, evasion=5,
        dmg_vs_ground=1,
    ),
    UnitType.TANK: UnitStats(
        build_cost_money=Decimal("90000"),
        build_cost_resources={ResourceType.STEEL: Decimal("600")},
        upkeep_money_per_day=Decimal("78"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("1728")},
        capacity_slots=6, attack=15, accuracy=85, evasion=5,
        dmg_vs_ground=15,
    ),
    UnitType.ARTILLERY: UnitStats(
        build_cost_money=Decimal("140000"),
        build_cost_resources={ResourceType.STEEL: Decimal("700")},
        upkeep_money_per_day=Decimal("121"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("1382")},
        capacity_slots=4, attack=10, accuracy=80, evasion=5,
        dmg_vs_ground=25,
    ),
    UnitType.FIGHTER: UnitStats(
        build_cost_money=Decimal("180000"),
        build_cost_resources={ResourceType.STEEL: Decimal("800")},
        upkeep_money_per_day=Decimal("156"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("3456")},
        capacity_slots=2, attack=40, accuracy=90, evasion=30,
        dmg_vs_ground=20, dmg_vs_air=40,
    ),
    UnitType.BOMBER: UnitStats(
        build_cost_money=Decimal("350000"),
        build_cost_resources={ResourceType.STEEL: Decimal("1400")},
        upkeep_money_per_day=Decimal("302"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("5184")},
        capacity_slots=2, attack=90, accuracy=85, evasion=10,
        dmg_vs_ground=135, dmg_vs_naval=135,
    ),
    UnitType.TRANSPORT_PLANE: UnitStats(
        build_cost_money=Decimal("150000"),
        build_cost_resources={ResourceType.STEEL: Decimal("1000")},
        upkeep_money_per_day=Decimal("130"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("2074")},
        capacity_slots=5, attack=0, accuracy=0, evasion=10, cargo_capacity=30,
    ),
    UnitType.DESTROYER: UnitStats(
        build_cost_money=Decimal("240000"),
        build_cost_resources={ResourceType.STEEL: Decimal("1500")},
        upkeep_money_per_day=Decimal("207"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("4147")},
        capacity_slots=3, attack=60, accuracy=85, evasion=10,
        dmg_vs_air=30, dmg_vs_naval=60,
    ),
    UnitType.SUBMARINE: UnitStats(
        build_cost_money=Decimal("320000"),
        build_cost_resources={ResourceType.STEEL: Decimal("2000")},
        upkeep_money_per_day=Decimal("276"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("3456")},
        capacity_slots=4, attack=80, accuracy=90, evasion=30,
        dmg_vs_naval=120,
    ),
    UnitType.CARRIER: UnitStats(
        build_cost_money=Decimal("700000"),
        build_cost_resources={ResourceType.STEEL: Decimal("4000")},
        upkeep_money_per_day=Decimal("605"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("10368")},
        capacity_slots=10, attack=70, accuracy=90, evasion=10,
        dmg_vs_naval=70,
    ),
    UnitType.TRANSPORT_SHIP: UnitStats(
        build_cost_money=Decimal("150000"),
        build_cost_resources={ResourceType.STEEL: Decimal("1000")},
        upkeep_money_per_day=Decimal("130"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("2074")},
        capacity_slots=5, attack=0, accuracy=0, evasion=10, cargo_capacity=50,
    ),
    UnitType.SHORT_RANGE_MISSILE: UnitStats(
        build_cost_money=Decimal("125000"),
        build_cost_resources={ResourceType.STEEL: Decimal("400")},
        upkeep_money_per_day=Decimal("108"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("346")},
        capacity_slots=1, attack=90, accuracy=90, evasion=0,
        dmg_vs_ground=12, dmg_vs_naval=12,
    ),
    UnitType.LONG_RANGE_MISSILE: UnitStats(
        build_cost_money=Decimal("350000"),
        build_cost_resources={ResourceType.STEEL: Decimal("1400")},
        upkeep_money_per_day=Decimal("302"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("5184")},
        capacity_slots=2, attack=135, accuracy=85, evasion=0,
        dmg_vs_ground=135, dmg_vs_naval=135,
    ),
    UnitType.AIR_DEFENSE: UnitStats(
        build_cost_money=Decimal("110000"),
        build_cost_resources={ResourceType.STEEL: Decimal("500")},
        upkeep_money_per_day=Decimal("95"),
        upkeep_resources_per_day={ResourceType.OIL: Decimal("346")},
        capacity_slots=1, attack=0, accuracy=85, evasion=5,
        dmg_vs_air=40,
    ),
}


class CountryUnit(Base):
    """تعداد یگان‌های یک کشور از یک نوع مشخص."""

    __tablename__ = "country_units"
    __table_args__ = (
        UniqueConstraint("country_id", "unit_type", name="uq_country_unit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    unit_type: Mapped[UnitType] = mapped_column(SAEnum(UnitType, native_enum=False))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
