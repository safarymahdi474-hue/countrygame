import datetime as dt
from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.models.resources import ResourceType
from bot.services.scheduler import _production_job, _season_advance_job
from bot.services.wallet import get_balance

pytestmark = pytest.mark.asyncio


async def test_production_job_grants_resources(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE, season_length_days=30)
        session.add(world)
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        country = Country(world_id=world.id, owner_id=user.id, nation_code="IT",
                           display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        session.add(country)
        await session.flush()
        session.add(CountryBuilding(country_id=country.id, building_type=BuildingType.STEEL_MINE, level=2))
        country_id = country.id
        await session.commit()

    await _production_job(session_factory, 3600)

    async with session_factory() as session:
        steel = await get_balance(session, country_id, ResourceType.STEEL)
        assert steel > 0


async def test_season_advance_job_ends_expired_world(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE, season_length_days=30)
        world.ends_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        session.add(world)
        await session.commit()
        world_id = world.id

    await _season_advance_job(session_factory)

    async with session_factory() as session:
        world = await session.get(World, world_id)
        assert world.status == WorldStatus.ENDED
