from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, User, World, WorldStatus
from bot.services import identity

pytestmark = pytest.mark.asyncio


async def test_get_telegram_id_for_country(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        user = User(telegram_id=987654, username="someone")
        session.add(user)
        await session.flush()
        country = Country(world_id=world.id, owner_id=user.id, nation_code="IT",
                           display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        session.add(country)
        await session.flush()
        country_id = country.id
        await session.commit()

    async with session_factory() as session:
        tg_id = await identity.get_telegram_id_for_country(session, country_id)
        assert tg_id == 987654


async def test_get_telegram_id_for_missing_country_returns_none(session_factory):
    async with session_factory() as session:
        tg_id = await identity.get_telegram_id_for_country(session, 999999)
        assert tg_id is None


async def test_create_country_uses_tier_starting_treasury(session_factory):
    from bot.models.country import CountryTier
    from bot.services.economy import STARTING_TREASURY

    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        world_id, user_id = world.id, user.id
        await session.commit()

    async with session_factory() as session:
        country = await identity.create_country(
            session, user_id=user_id, world_id=world_id,
            nation_code="EG", display_name="Egypt", tier=CountryTier.ELITE,
        )
        await session.commit()
        assert country.treasury == STARTING_TREASURY[CountryTier.ELITE]
