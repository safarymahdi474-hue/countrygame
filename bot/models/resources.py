from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.engine import Base


class ResourceType(str, enum.Enum):
    STEEL = "steel"
    OIL = "oil"
    URANIUM = "uranium"
    FOOD = "food"
    POWER = "power"


class CountryResource(Base):
    """موجودی انبار هر نوع منبع برای یک کشور."""

    __tablename__ = "country_resources"
    __table_args__ = (
        UniqueConstraint("country_id", "resource_type", name="uq_country_resource"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, native_enum=False)
    )
    amount: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)
    capacity: Mapped[Numeric | None] = mapped_column(Numeric(18, 2), nullable=True)
