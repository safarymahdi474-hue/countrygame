from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, CountryUnit, UnitType, User, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.services import ranking, scoring, season, subscription

pytestmark = pytest.mark.asyncio


async def test_leaderboard_ranks_stronger_country_first(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.UPCOMING, season_length_days=30)
        session.add(world)
        await session.flush()
        u1 = User(telegram_id=1, username="a")
        u2 = User(telegram_id=2, username="b")
        session.add_all([u1, u2])
        await session.flush()

        strong = Country(world_id=world.id, owner_id=u1.id, nation_code="IT",
                          display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("2000000"))
        weak = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                        display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("100000"))
        session.add_all([strong, weak])
        await session.flush()

        session.add(CountryBuilding(country_id=strong.id, building_type=BuildingType.STEEL_MINE, level=5))
        session.add(CountryBuilding(country_id=strong.id, building_type=BuildingType.HOSPITAL, level=3))
        session.add(CountryUnit(country_id=strong.id, unit_type=UnitType.TANK, quantity=50))
        session.add(CountryBuilding(country_id=weak.id, building_type=BuildingType.STEEL_MINE, level=1))

        world_id, strong_id, weak_id = world.id, strong.id, weak.id
        await session.commit()

    async with session_factory() as session:
        w = await season.start_world(session, world_id)
        await session.commit()
        assert w.status == WorldStatus.ACTIVE
        assert w.ends_at is not None

    async with session_factory() as session:
        await scoring.recompute_scores(session, strong_id)
        await scoring.recompute_scores(session, weak_id)
        await session.commit()

    async with session_factory() as session:
        leaderboard = await ranking.compute_leaderboard(session, world_id)
        assert leaderboard[0].country_id == strong_id

    async with session_factory() as session:
        w = await season.end_world(session, world_id)
        await session.commit()
        assert w.status == WorldStatus.ENDED


async def test_vip_activation_and_fee_waiver(session_factory):
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
        assert await subscription.is_vip(session, country_id) is False
        await subscription.activate_vip(session, country_id, duration_days=7)
        await session.commit()

    async with session_factory() as session:
        assert await subscription.is_vip(session, country_id) is True
        assert await subscription.market_fee_rate(session, country_id) == Decimal("0")
