import random
from decimal import Decimal

import pytest

from bot.models import BuildingType, Country, CountryTier, User, UnitType, World, WorldStatus
from bot.models.buildings import CountryBuilding
from bot.models.military import CountryUnit, UnitCategory
from bot.models.resources import ResourceType
from bot.services.combat import resolve_attack
from bot.services.economy import lab_unit_cost_discount, radar_missile_reduction
from bot.services.military import build_units
from bot.services.wallet import adjust_balance, get_balance

pytestmark = pytest.mark.asyncio


async def test_radar_and_lab_formulas():
    assert radar_missile_reduction(0) == Decimal("0")
    assert radar_missile_reduction(5) == Decimal("0.2")  # 5 * 4%
    assert radar_missile_reduction(100) == Decimal("0.6")  # سقف ۶۰٪

    assert lab_unit_cost_discount(0) == Decimal("0")
    assert lab_unit_cost_discount(5) == Decimal("0.15")  # 5 * 3%
    assert lab_unit_cost_discount(100) == Decimal("0.5")  # سقف ۵۰٪


async def _make_two_countries(session_factory, treasury1="10000000", treasury2="10000000"):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        u1 = User(telegram_id=1, username="a")
        u2 = User(telegram_id=2, username="b")
        session.add_all([u1, u2])
        await session.flush()
        c1 = Country(world_id=world.id, owner_id=u1.id, nation_code="IT",
                      display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal(treasury1))
        c2 = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                      display_name="France", tier=CountryTier.STANDARD, treasury=Decimal(treasury2))
        session.add_all([c1, c2])
        await session.flush()
        world_id, c1_id, c2_id = world.id, c1.id, c2.id
        await session.commit()
    return world_id, c1_id, c2_id


async def test_lab_reduces_unit_build_cost(session_factory):
    _, c1_id, _ = await _make_two_countries(session_factory)

    async with session_factory() as session:
        session.add(CountryBuilding(country_id=c1_id, building_type=BuildingType.LAB, level=5))
        session.add(CountryBuilding(country_id=c1_id, building_type=BuildingType.GARRISON, level=5))
        await session.commit()

    async with session_factory() as session:
        await adjust_balance(session, c1_id, ResourceType.STEEL, Decimal("5000"))
        await session.commit()

    async with session_factory() as session:
        await build_units(session, c1_id, UnitType.INFANTRY, 100)  # هزینه پایه: 100*8000=800000
        await session.commit()

    async with session_factory() as session:
        treasury = await get_balance(session, c1_id, None)
        # با ۱۵٪ تخفیف: 800000 * 0.85 = 680000
        assert treasury == Decimal("10000000") - Decimal("680000")


async def test_radar_reduces_incoming_missile_power(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()
        u1 = User(telegram_id=1, username="a")
        u2 = User(telegram_id=2, username="b")
        u3 = User(telegram_id=3, username="c")
        session.add_all([u1, u2, u3])
        await session.flush()

        attacker = Country(world_id=world.id, owner_id=u1.id, nation_code="IT",
                            display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        shielded = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                            display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        unshielded = Country(world_id=world.id, owner_id=u3.id, nation_code="DE",
                              display_name="Germany", tier=CountryTier.STANDARD, treasury=Decimal("0"))
        session.add_all([attacker, shielded, unshielded])
        await session.flush()

        session.add(CountryBuilding(country_id=shielded.id, building_type=BuildingType.RADAR, level=5))
        session.add(CountryUnit(country_id=attacker.id, unit_type=UnitType.LONG_RANGE_MISSILE, quantity=100))

        world_id = world.id
        attacker_id, shielded_id, unshielded_id = attacker.id, shielded.id, unshielded.id
        await session.commit()

    async with session_factory() as session:
        rng = random.Random(1)
        result_with_radar = await resolve_attack(
            session, world_id=world_id, attacker_country_id=attacker_id, defender_country_id=shielded_id,
            category=UnitCategory.MISSILE, attack_order={UnitType.LONG_RANGE_MISSILE: 10}, rng=rng,
        )

    async with session_factory() as session:
        rng = random.Random(1)  # همون seed، ولی کشور بدون رادار
        result_without_radar = await resolve_attack(
            session, world_id=world_id, attacker_country_id=attacker_id, defender_country_id=unshielded_id,
            category=UnitCategory.MISSILE, attack_order={UnitType.LONG_RANGE_MISSILE: 10}, rng=rng,
        )

    assert result_with_radar.attacker_power < result_without_radar.attacker_power
