from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.subscription import CountrySubscription, SubscriptionTier

# --- مزایای VIP — طراحی خودمون ---
VIP_CONSTRUCTION_TIME_MULTIPLIER = Decimal("0.8")   # ۲۰٪ سریع‌تر
VIP_RESEARCH_TIME_MULTIPLIER = Decimal("0.8")       # ۲۰٪ سریع‌تر
VIP_MAX_PARALLEL_QUEUES = 2                         # به‌جای ۱ صف، ۲ صف هم‌زمان
VIP_MARKET_FEE_RATE = Decimal("0")                  # بدون کارمزد بازار/انتقال
STANDARD_MARKET_FEE_RATE = Decimal("0.02")          # ۲٪ کارمزد برای کاربر عادی


async def is_vip(session: AsyncSession, country_id: int) -> bool:
    result = await session.execute(
        select(CountrySubscription).where(CountrySubscription.country_id == country_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None or sub.tier != SubscriptionTier.VIP:
        return False
    if sub.expires_at is None:
        return True  # اشتراک نامحدود
    expires_at = sub.expires_at
    if expires_at.tzinfo is None:
        # بعضی درایورها (مثل sqlite) تایم‌زون رو موقع خوندن حفظ نمی‌کنن؛
        # فرض می‌کنیم چیزی که ذخیره شده UTC بوده.
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    return expires_at > dt.datetime.now(dt.timezone.utc)


async def activate_vip(
    session: AsyncSession, country_id: int, *, duration_days: int
) -> CountrySubscription:
    result = await session.execute(
        select(CountrySubscription).where(CountrySubscription.country_id == country_id)
    )
    sub = result.scalar_one_or_none()
    now = dt.datetime.now(dt.timezone.utc)
    new_expiry = now + dt.timedelta(days=duration_days)

    if sub is None:
        sub = CountrySubscription(
            country_id=country_id, tier=SubscriptionTier.VIP, expires_at=new_expiry
        )
        session.add(sub)
        return sub

    # اگه از قبل فعال بود، روزها رو جمع می‌کنیم (تمدید)، نه جایگزین
    existing_expiry = sub.expires_at
    if existing_expiry is not None and existing_expiry.tzinfo is None:
        existing_expiry = existing_expiry.replace(tzinfo=dt.timezone.utc)
    base = existing_expiry if (existing_expiry and existing_expiry > now) else now
    sub.tier = SubscriptionTier.VIP
    sub.expires_at = base + dt.timedelta(days=duration_days)
    return sub


async def construction_time_multiplier(session: AsyncSession, country_id: int) -> Decimal:
    return VIP_CONSTRUCTION_TIME_MULTIPLIER if await is_vip(session, country_id) else Decimal("1")


async def market_fee_rate(session: AsyncSession, country_id: int) -> Decimal:
    return VIP_MARKET_FEE_RATE if await is_vip(session, country_id) else STANDARD_MARKET_FEE_RATE


async def max_parallel_queues(session: AsyncSession, country_id: int) -> int:
    return VIP_MAX_PARALLEL_QUEUES if await is_vip(session, country_id) else 1
