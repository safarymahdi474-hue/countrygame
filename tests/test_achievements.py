from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.services import achievements, season

pytestmark = pytest.mark.asyncio


async def test_season_champion_gets_achievement_on_world_end(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE, season_length_days=30)
        session.add(world)
        await session.flush()
        u1 = User(telegram_id=1, username="a")
        u2 = User(telegram_id=2, username="b")
        session.add_all([u1, u2])
        await session.flush()

        strong = Country(world_id=world.id, owner_id=u1.id, nation_code="IT",
                          display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("5000000"))
        weak = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                        display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("1000"))
        session.add_all([strong, weak])
        await session.flush()
        session.add(CountryBuilding(country_id=strong.id, building_type=BuildingType.STEEL_MINE, level=5))

        world_id, strong_id = world.id, strong.id
        await session.commit()

    async with session_factory() as session:
        await season.end_world(session, world_id)
        await session.commit()

    async with session_factory() as session:
        items = await achievements.list_achievements(session, strong_id)
        assert len(items) == 1
        assert "قهرمان فصل" in items[0].title


async def test_no_achievement_for_empty_world(session_factory):
    async with session_factory() as session:
        world = World(name="EmptyWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.commit()
        world_id = world.id

    async with session_factory() as session:
        champion = await achievements.award_season_champion(session, world_id)
        assert champion is None
