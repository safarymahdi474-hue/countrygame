from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, User, UnitType, World, WorldStatus
from bot.models.military import CountryUnit
from bot.services.combat import AmphibiousError, resolve_amphibious_attack

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
                      display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("500000"))
        session.add_all([c1, c2])
        await session.flush()
        world_id, c1_id, c2_id = world.id, c1.id, c2.id
        await session.commit()
    return world_id, c1_id, c2_id


async def test_amphibious_attack_needs_transport_ships(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)
    async with session_factory() as session:
        session.add(CountryUnit(country_id=c1_id, unit_type=UnitType.TANK, quantity=10))
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(AmphibiousError, match="ناو ترابری کافی نیست"):
            await resolve_amphibious_attack(
                session, world_id=world_id, attacker_country_id=c1_id, defender_country_id=c2_id,
                transport_ship_quantity=1, ground_attack_order={UnitType.TANK: 10},
            )


async def test_amphibious_attack_needs_enough_cargo_capacity(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)
    async with session_factory() as session:
        session.add(CountryUnit(country_id=c1_id, unit_type=UnitType.TANK, quantity=100))  # 100*6=600 slots
        session.add(CountryUnit(country_id=c1_id, unit_type=UnitType.TRANSPORT_SHIP, quantity=1))  # فقط 50 جا
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(AmphibiousError, match="ظرفیت حمل کافی نیست"):
            await resolve_amphibious_attack(
                session, world_id=world_id, attacker_country_id=c1_id, defender_country_id=c2_id,
                transport_ship_quantity=1, ground_attack_order={UnitType.TANK: 100},
            )


async def test_amphibious_attack_succeeds_with_enough_capacity(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)
    async with session_factory() as session:
        session.add(CountryUnit(country_id=c1_id, unit_type=UnitType.TANK, quantity=8))  # 8*6=48 slots
        session.add(CountryUnit(country_id=c1_id, unit_type=UnitType.TRANSPORT_SHIP, quantity=1))  # 50 جا
        await session.commit()

    async with session_factory() as session:
        result = await resolve_amphibious_attack(
            session, world_id=world_id, attacker_country_id=c1_id, defender_country_id=c2_id,
            transport_ship_quantity=1, ground_attack_order={UnitType.TANK: 8},
        )
        await session.commit()
        assert result.winner == "attacker"  # هیچ مدافعی نداره، پس حتماً می‌بره


async def test_amphibious_rejects_non_ground_units(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)
    async with session_factory() as session:
        with pytest.raises(AmphibiousError, match="یگان زمینی نیست"):
            await resolve_amphibious_attack(
                session, world_id=world_id, attacker_country_id=c1_id, defender_country_id=c2_id,
                transport_ship_quantity=1, ground_attack_order={UnitType.FIGHTER: 1},
            )
