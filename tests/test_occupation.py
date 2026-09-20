import datetime as dt
from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.services import occupation, scoring
from bot.services.occupation import OccupationError, can_occupy, occupy_country
from bot.services.production_tick import run_production_tick
from bot.services.wallet import get_balance
from bot.models.resources import ResourceType

pytestmark = pytest.mark.asyncio


async def _make_two_countries(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        u1 = User(telegram_id=1, username="a")
        u2 = User(telegram_id=2, username="b")
        session.add_all([u1, u2])
        await session.flush()
        c1 = Country(world_id=world.id, owner_id=u1.id, nation_code="IT",
                      display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        c2 = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                      display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        session.add_all([c1, c2])
        await session.flush()
        session.add(CountryBuilding(country_id=c2.id, building_type=BuildingType.STEEL_MINE, level=2))
        c1_id, c2_id = c1.id, c2.id
        await session.commit()
    return c1_id, c2_id


async def test_can_occupy_threshold():
    assert can_occupy(Decimal("100"), Decimal("10")) is True   # اختلاف زیاد
    assert can_occupy(Decimal("100"), Decimal("90")) is False  # اختلاف کم


async def test_occupy_and_liberate(session_factory):
    c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        target = await occupy_country(session, occupier_country_id=c1_id, target_country_id=c2_id)
        await session.commit()
        assert target.occupied_by_id == c1_id

    async with session_factory() as session:
        assert await occupation.is_occupied(session, c2_id) is True
        assert await occupation.count_occupied_by(session, c1_id) == 1

    # دستی منقضی‌ش می‌کنیم و چک می‌کنیم liberate کار می‌کنه
    async with session_factory() as session:
        country = await session.get(Country, c2_id)
        country.occupied_until = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        await session.commit()

    async with session_factory() as session:
        liberated = await occupation.liberate_expired_occupations(session)
        await session.commit()
        assert len(liberated) == 1
        assert liberated[0].id == c2_id

    async with session_factory() as session:
        assert await occupation.is_occupied(session, c2_id) is False


async def test_cannot_occupy_self(session_factory):
    c1_id, _ = await _make_two_countries(session_factory)
    async with session_factory() as session:
        with pytest.raises(OccupationError):
            await occupy_country(session, occupier_country_id=c1_id, target_country_id=c1_id)


async def test_production_halved_while_occupied(session_factory):
    c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        steel_before = await run_production_tick(session, c2_id, elapsed_seconds=3600)
        await session.rollback()  # این رو فقط برای اندازه‌گیریِ بدون اشغال محاسبه کردیم، ذخیره نمی‌کنیم

    async with session_factory() as session:
        await occupy_country(session, occupier_country_id=c1_id, target_country_id=c2_id)
        await session.commit()

    async with session_factory() as session:
        steel_while_occupied = await run_production_tick(session, c2_id, elapsed_seconds=3600)
        await session.commit()

    from bot.models.resources import ResourceType as RT
    assert steel_while_occupied[RT.STEEL] == steel_before[RT.STEEL] * Decimal("0.5")


async def test_territory_score_reflects_occupation(session_factory):
    c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        await occupy_country(session, occupier_country_id=c1_id, target_country_id=c2_id)
        await session.commit()

    async with session_factory() as session:
        country = await scoring.recompute_scores(session, c1_id)
        await session.commit()
        assert country.score_territory >= Decimal("50")
