from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.diplomacy import BorderStatus, CountryBorderPolicy
from bot.models.market import ListingStatus, MarketListing
from bot.models.resources import ResourceType
from bot.services import subscription, world_events
from bot.services.wallet import adjust_balance, get_balance


class MarketError(Exception):
    pass


async def _trade_border_open(session: AsyncSession, country_id: int) -> bool:
    result = await session.execute(
        select(CountryBorderPolicy.trade_status).where(
            CountryBorderPolicy.country_id == country_id
        )
    )
    status = result.scalar_one_or_none()
    # اگه هنوز policy ساخته نشده، طبق پیش‌فرض مدل، تجاری بازه
    return status is None or status != BorderStatus.CLOSED


async def create_listing(
    session: AsyncSession,
    *,
    world_id: int,
    seller_country_id: int,
    offer_resource: ResourceType | None,
    offer_amount: Decimal,
    request_resource: ResourceType | None,
    request_amount: Decimal,
) -> MarketListing:
    if offer_amount <= 0 or request_amount <= 0:
        raise MarketError("مقدار عرضه و درخواست باید مثبت باشه.")
    if offer_resource == request_resource:
        raise MarketError("نمی‌تونی یک کالا رو با همون کالا معامله کنی.")
    if not await _trade_border_open(session, seller_country_id):
        raise MarketError("مرز تجاری کشورت بسته‌ست.")

    # کالای عرضه‌شده رو همین الان به‌صورت امانت (escrow) از کشور کم می‌کنیم
    # تا نتونه همون رو جای دیگه هم بفروشه یا خرج کنه.
    await adjust_balance(session, seller_country_id, offer_resource, -offer_amount, source="market:listing_escrow")

    listing = MarketListing(
        world_id=world_id,
        seller_country_id=seller_country_id,
        offer_resource=offer_resource,
        offer_amount=offer_amount,
        request_resource=request_resource,
        request_amount=request_amount,
        status=ListingStatus.OPEN,
    )
    session.add(listing)
    return listing


async def cancel_listing(session: AsyncSession, listing_id: int, requester_country_id: int) -> None:
    result = await session.execute(select(MarketListing).where(MarketListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise MarketError("آگهی پیدا نشد.")
    if listing.seller_country_id != requester_country_id:
        raise MarketError("این آگهی مال تو نیست.")
    if listing.status != ListingStatus.OPEN:
        raise MarketError("این آگهی دیگه باز نیست.")

    # برگردوندن امانت
    await adjust_balance(session, listing.seller_country_id, listing.offer_resource, listing.offer_amount, source="market:cancel_refund")
    listing.status = ListingStatus.CANCELLED


async def accept_listing(
    session: AsyncSession, listing_id: int, buyer_country_id: int
) -> MarketListing:
    result = await session.execute(select(MarketListing).where(MarketListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None:
        raise MarketError("آگهی پیدا نشد.")
    if listing.status != ListingStatus.OPEN:
        raise MarketError("این آگهی دیگه باز نیست.")
    if listing.seller_country_id == buyer_country_id:
        raise MarketError("نمی‌تونی آگهی خودت رو بخری.")
    if not await _trade_border_open(session, buyer_country_id):
        raise MarketError("مرز تجاری کشورت بسته‌ست.")

    balance = await get_balance(session, buyer_country_id, listing.request_resource)
    if balance < listing.request_amount:
        raise MarketError("موجودی کافی برای پرداخت نداری.")

    # خریدار: کالای درخواستی رو می‌ده، کالای عرضه‌شده رو می‌گیره
    await adjust_balance(session, buyer_country_id, listing.request_resource, -listing.request_amount, source="market:purchase")
    await adjust_balance(session, buyer_country_id, listing.offer_resource, listing.offer_amount, source="market:purchase")

    # فروشنده: کالای درخواستی رو می‌گیره، منهای کارمزد بازار (VIP کارمزد نداره)
    fee_rate = await subscription.market_fee_rate(session, listing.seller_country_id)
    active_event = await world_events.get_active_event(session, listing.world_id)
    fee_rate = max(Decimal("0"), fee_rate + world_events.market_fee_delta(active_event))
    fee = (listing.request_amount * fee_rate).quantize(Decimal("0.01"))
    seller_receives = listing.request_amount - fee
    await adjust_balance(session, listing.seller_country_id, listing.request_resource, seller_receives, source="market:sale")

    listing.status = ListingStatus.COMPLETED
    listing.buyer_country_id = buyer_country_id
    listing.completed_at = dt.datetime.now(dt.timezone.utc)

    return listing


async def list_open_listings(
    session: AsyncSession, *, world_id: int, exclude_seller_id: int | None = None, limit: int = 15
) -> list[MarketListing]:
    query = select(MarketListing).where(
        MarketListing.world_id == world_id, MarketListing.status == ListingStatus.OPEN
    )
    if exclude_seller_id is not None:
        query = query.where(MarketListing.seller_country_id != exclude_seller_id)
    query = query.order_by(MarketListing.created_at.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def list_my_listings(
    session: AsyncSession, *, seller_country_id: int, limit: int = 15
) -> list[MarketListing]:
    result = await session.execute(
        select(MarketListing)
        .where(
            MarketListing.seller_country_id == seller_country_id,
            MarketListing.status == ListingStatus.OPEN,
        )
        .order_by(MarketListing.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
