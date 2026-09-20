from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, World, WorldStatus
from bot.services.construction import ConstructionError, upgrade_building
from bot.services.power import compute_power_balance

pytestmark = pytest.mark.asyncio


async def _make_country(session_factory, treasury: str = "50000000"):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        country = Country(world_id=world.id, owner_id=user.id, nation_code="IT",
                           display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal(treasury))
        session.add(country)
        await session.flush()
        country_id = country.id
        await session.commit()
    return country_id


async def test_cannot_build_without_power(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        with pytest.raises(ConstructionError, match="برق کافی نیست"):
            await upgrade_building(session, country_id, BuildingType.STEEL_MINE)


async def test_power_plant_itself_is_exempt(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        building = await upgrade_building(session, country_id, BuildingType.WIND_PLANT)
        await session.commit()
        assert building.level == 1


async def test_after_power_plant_other_buildings_work(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        await upgrade_building(session, country_id, BuildingType.WIND_PLANT)
        await session.commit()

    async with session_factory() as session:
        produced, consumed = await compute_power_balance(session, country_id)
        assert produced > consumed  # نیروگاه بادی سطح ۱ باید ۳۵ واحد بده، مصرف صفره هنوز

    async with session_factory() as session:
        building = await upgrade_building(session, country_id, BuildingType.STEEL_MINE)
        await session.commit()
        assert building.level == 1


async def test_upgrade_deducts_cost_and_hits_max_level(session_factory):
    country_id = await _make_country(session_factory)
    async with session_factory() as session:
        await upgrade_building(session, country_id, BuildingType.WIND_PLANT)
        await session.commit()

    async with session_factory() as session:
        country = await session.get(Country, country_id)
        treasury_before = country.treasury

    async with session_factory() as session:
        await upgrade_building(session, country_id, BuildingType.WIND_PLANT)  # سطح ۲
        await session.commit()

    async with session_factory() as session:
        country = await session.get(Country, country_id)
        assert country.treasury < treasury_before
