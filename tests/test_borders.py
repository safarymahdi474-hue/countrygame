from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, User, World, WorldStatus
from bot.models.diplomacy import BorderStatus
from bot.services import diplomacy

pytestmark = pytest.mark.asyncio


async def test_border_policy_defaults_and_update(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        country = Country(world_id=world.id, owner_id=user.id, nation_code="IT",
                           display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        session.add(country)
        await session.flush()
        country_id = country.id
        await session.commit()

    async with session_factory() as session:
        policy = await diplomacy.get_or_create_border_policy(session, country_id)
        assert policy.ground_status == BorderStatus.CLOSED
        assert policy.air_status == BorderStatus.CLOSED
        assert policy.naval_status == BorderStatus.CLOSED
        assert policy.trade_status == BorderStatus.OPEN
        await session.commit()

    async with session_factory() as session:
        await diplomacy.set_border_status(session, country_id, "ground_status", BorderStatus.OPEN)
        await session.commit()

    async with session_factory() as session:
        policy = await diplomacy.get_or_create_border_policy(session, country_id)
        assert policy.ground_status == BorderStatus.OPEN
