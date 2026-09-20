from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country, CountryTier
from bot.models.user import User
from bot.models.world import World, WorldStatus
from bot.services.economy import STARTING_TREASURY


class IdentityError(Exception):
    pass


async def get_or_create_user(
    session: AsyncSession, *, telegram_id: int, username: str | None
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        if username and user.username != username:
            user.username = username
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def get_country_for_user(
    session: AsyncSession, *, user_id: int, world_id: int
) -> Country | None:
    result = await session.execute(
        select(Country).where(Country.owner_id == user_id, Country.world_id == world_id)
    )
    return result.scalar_one_or_none()


async def list_countries_for_user(session: AsyncSession, *, user_id: int) -> list[Country]:
    result = await session.execute(
        select(Country).where(Country.owner_id == user_id).order_by(Country.created_at)
    )
    return list(result.scalars().all())


async def create_country(
    session: AsyncSession,
    *,
    user_id: int,
    world_id: int,
    nation_code: str,
    display_name: str,
    tier: CountryTier = CountryTier.STANDARD,
) -> Country:
    existing = await get_country_for_user(session, user_id=user_id, world_id=world_id)
    if existing is not None:
        raise IdentityError("این کاربر از قبل تو این دنیا کشور داره.")

    taken = await session.execute(
        select(Country).where(Country.world_id == world_id, Country.nation_code == nation_code)
    )
    if taken.scalar_one_or_none() is not None:
        raise IdentityError("این کشور تو این دنیا قبلاً انتخاب شده.")

    country = Country(
        world_id=world_id,
        owner_id=user_id,
        nation_code=nation_code,
        display_name=display_name,
        tier=tier,
        treasury=STARTING_TREASURY[tier],
    )
    session.add(country)
    await session.flush()
    return country


async def list_other_countries(
    session: AsyncSession, *, world_id: int, exclude_country_id: int, limit: int = 20
) -> list[Country]:
    result = await session.execute(
        select(Country)
        .where(Country.world_id == world_id, Country.id != exclude_country_id)
        .order_by(Country.display_name)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_telegram_id_for_country(session: AsyncSession, country_id: int) -> int | None:
    """برای اطلاع‌رسانی (حمله، پیمان و ...) — آی‌دی تلگرامِ صاحبِ یه کشور رو برمی‌گردونه."""
    result = await session.execute(
        select(User.telegram_id).join(Country, Country.owner_id == User.id).where(
            Country.id == country_id
        )
    )
    return result.scalar_one_or_none()


async def set_current_world(session: AsyncSession, user_id: int, world_id: int) -> None:
    user = await session.get(User, user_id)
    if user is not None:
        user.current_world_id = world_id


async def get_active_world_for_user(session: AsyncSession, user: User) -> World:
    """
    دنیایی که کاربر الان توش فعاله. اگه current_world_id ست شده و اون
    دنیا هنوز فعاله، همون رو برمی‌گردونه؛ وگرنه (اولین بار، یا دنیاش
    تموم شده) میفته رو دنیای فعالِ پیش‌فرض و همون رو به‌عنوان current ثبت می‌کنه.
    """
    from bot.services.season import get_or_create_active_world

    if user.current_world_id is not None:
        world = await session.get(World, user.current_world_id)
        if world is not None and world.status == WorldStatus.ACTIVE:
            return world

    world = await get_or_create_active_world(session)
    user.current_world_id = world.id
    return world
