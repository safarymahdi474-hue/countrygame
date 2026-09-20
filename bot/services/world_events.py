"""
رویدادهای جهانی — طراحی خودمون، برخلاف بازیِ منبعِ الهام که صریحاً
می‌گفت «فصل‌ها هیچ اثری روی اقتصاد ندارن». اینجا هر چند روز یک‌بار،
به‌صورت تصادفی یه رویداد رو کل یه دنیا اثر می‌ذاره — هم مثبت هم منفی،
تا بازی قابل‌پیش‌بینی نمونه.
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.resources import ResourceType
from bot.models.world_event import WorldEvent, WorldEventType

EVENT_DURATION_DAYS = 3


@dataclass(frozen=True, slots=True)
class EventEffect:
    resource_multipliers: dict[ResourceType, Decimal] = field(default_factory=dict)
    market_fee_delta: Decimal = Decimal("0")  # به نرخ کارمزد پایه اضافه/کم می‌شه
    description: str = ""


EVENT_EFFECTS: dict[WorldEventType, EventEffect] = {
    WorldEventType.DROUGHT: EventEffect(
        resource_multipliers={ResourceType.FOOD: Decimal("0.5")},
        description="🌵 خشکسالی — تولید غذا ۵۰٪ کم شده",
    ),
    WorldEventType.TRADE_BOOM: EventEffect(
        market_fee_delta=Decimal("-0.02"),  # کارمزد استاندارد رو صفر می‌کنه
        description="📈 رونق تجاری — کارمزد بازار جهانی صفر شده",
    ),
    WorldEventType.ENERGY_CRISIS: EventEffect(
        resource_multipliers={},  # برق تو انبار ذخیره نمی‌شه؛ اثرش جدا در power.py اعمال می‌شه
        description="🔌 بحران انرژی — تولید نیروگاه‌ها ۳۰٪ کم شده",
    ),
    WorldEventType.STEEL_SHORTAGE: EventEffect(
        resource_multipliers={ResourceType.STEEL: Decimal("0.6")},
        description="⚙️ کمبود فولاد — تولید فولاد ۴۰٪ کم شده",
    ),
    WorldEventType.OIL_BOOM: EventEffect(
        resource_multipliers={ResourceType.OIL: Decimal("1.5")},
        description="🛢 رونق نفتی — تولید نفت ۵۰٪ زیاد شده",
    ),
    WorldEventType.BUMPER_HARVEST: EventEffect(
        resource_multipliers={ResourceType.FOOD: Decimal("1.4")},
        description="🌾 برداشت پرمحصول — تولید غذا ۴۰٪ زیاد شده",
    ),
}

POWER_MULTIPLIER_EVENTS: dict[WorldEventType, Decimal] = {
    WorldEventType.ENERGY_CRISIS: Decimal("0.7"),
}


async def get_active_event(session: AsyncSession, world_id: int) -> WorldEvent | None:
    now = dt.datetime.now(dt.timezone.utc)
    result = await session.execute(
        select(WorldEvent)
        .where(WorldEvent.world_id == world_id)
        .order_by(WorldEvent.started_at.desc())
        .limit(1)
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    ends_at = event.ends_at
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=dt.timezone.utc)
    return event if ends_at > now else None


async def roll_new_event(
    session: AsyncSession, world_id: int, *, rng: random.Random | None = None
) -> WorldEvent:
    rng = rng or random.Random()
    event_type = rng.choice(list(WorldEventType))
    now = dt.datetime.now(dt.timezone.utc)
    event = WorldEvent(
        world_id=world_id,
        event_type=event_type,
        started_at=now,
        ends_at=now + dt.timedelta(days=EVENT_DURATION_DAYS),
    )
    session.add(event)
    return event


def resource_multiplier(event: WorldEvent | None, resource: ResourceType) -> Decimal:
    if event is None:
        return Decimal("1")
    effect = EVENT_EFFECTS[event.event_type]
    return effect.resource_multipliers.get(resource, Decimal("1"))


def power_multiplier(event: WorldEvent | None) -> Decimal:
    if event is None:
        return Decimal("1")
    return POWER_MULTIPLIER_EVENTS.get(event.event_type, Decimal("1"))


def market_fee_delta(event: WorldEvent | None) -> Decimal:
    if event is None:
        return Decimal("0")
    return EVENT_EFFECTS[event.event_type].market_fee_delta
