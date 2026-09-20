import random
from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.models.resources import ResourceType
from bot.models.world_event import WorldEventType
from bot.services import world_events
from bot.services.power import compute_power_balance
from bot.services.production_tick import run_production_tick

pytestmark = pytest.mark.asyncio


async def _make_country(session_factory):
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
        world_id, country_id = world.id, country.id
        await session.commit()
    return world_id, country_id


async def test_no_event_means_no_effect(session_factory):
    world_id, _ = await _make_country(session_factory)
    async with session_factory() as session:
        event = await world_events.get_active_event(session, world_id)
        assert event is None
        assert world_events.resource_multiplier(event, ResourceType.FOOD) == Decimal("1")


async def test_roll_new_event_creates_active_event(session_factory):
    world_id, _ = await _make_country(session_factory)
    async with session_factory() as session:
        rng = random.Random(1)
        event = await world_events.roll_new_event(session, world_id, rng=rng)
        await session.commit()
        event_id = event.id

    async with session_factory() as session:
        active = await world_events.get_active_event(session, world_id)
        assert active is not None
        assert active.id == event_id


async def test_drought_halves_food_production(session_factory):
    world_id, country_id = await _make_country(session_factory)
    async with session_factory() as session:
        session.add(CountryBuilding(country_id=country_id, building_type=BuildingType.FARM, level=1))
        await session.commit()

    async with session_factory() as session:
        baseline = await run_production_tick(session, country_id, elapsed_seconds=3600)
        await session.rollback()

    async with session_factory() as session:
        from bot.models.world_event import WorldEvent
        import datetime as dt
        session.add(WorldEvent(
            world_id=world_id, event_type=WorldEventType.DROUGHT,
            ends_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1),
        ))
        await session.commit()

    async with session_factory() as session:
        with_drought = await run_production_tick(session, country_id, elapsed_seconds=3600)
        await session.commit()

    assert with_drought[ResourceType.FOOD] == baseline[ResourceType.FOOD] * Decimal("0.5")


async def test_energy_crisis_reduces_power_production(session_factory):
    world_id, country_id = await _make_country(session_factory)
    async with session_factory() as session:
        session.add(CountryBuilding(country_id=country_id, building_type=BuildingType.WIND_PLANT, level=1))
        await session.commit()

    async with session_factory() as session:
        produced_before, _ = await compute_power_balance(session, country_id)

    async with session_factory() as session:
        from bot.models.world_event import WorldEvent
        import datetime as dt
        session.add(WorldEvent(
            world_id=world_id, event_type=WorldEventType.ENERGY_CRISIS,
            ends_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1),
        ))
        await session.commit()

    async with session_factory() as session:
        produced_after, _ = await compute_power_balance(session, country_id)

    assert produced_after == produced_before * Decimal("0.7")


async def test_expired_event_is_not_active(session_factory):
    world_id, _ = await _make_country(session_factory)
    async with session_factory() as session:
        from bot.models.world_event import WorldEvent
        import datetime as dt
        session.add(WorldEvent(
            world_id=world_id, event_type=WorldEventType.DROUGHT,
            ends_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),  # قبلاً تموم شده
        ))
        await session.commit()

    async with session_factory() as session:
        active = await world_events.get_active_event(session, world_id)
        assert active is None
