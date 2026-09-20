import random
from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, User, World, WorldStatus
from bot.models.military import CountryUnit, UnitCategory, UnitType
from bot.services.combat import resolve_attack

pytestmark = pytest.mark.asyncio


async def test_strong_attacker_wins_and_loots(session_factory):
    async with session_factory() as session:
        world = World(name="TestWorld", status=WorldStatus.ACTIVE)
        session.add(world)
        await session.flush()

        user1 = User(telegram_id=111, username="attacker_user")
        user2 = User(telegram_id=222, username="defender_user")
        session.add_all([user1, user2])
        await session.flush()

        attacker = Country(
            world_id=world.id, owner_id=user1.id, nation_code="IT",
            display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("1000000"),
        )
        defender = Country(
            world_id=world.id, owner_id=user2.id, nation_code="FR",
            display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("500000"),
        )
        session.add_all([attacker, defender])
        await session.flush()

        session.add(CountryUnit(country_id=attacker.id, unit_type=UnitType.TANK, quantity=100))
        session.add(CountryUnit(country_id=defender.id, unit_type=UnitType.INFANTRY, quantity=20))

        await session.commit()
        attacker_id, defender_id, world_id = attacker.id, defender.id, world.id

    async with session_factory() as session:
        rng = random.Random(42)
        result = await resolve_attack(
            session,
            world_id=world_id,
            attacker_country_id=attacker_id,
            defender_country_id=defender_id,
            category=UnitCategory.GROUND,
            attack_order={UnitType.TANK: 100},
            rng=rng,
        )
        await session.commit()

        assert result.winner == "attacker"
        assert result.money_looted > 0
        assert result.attacker_power > result.defender_power

        attacker_after = await session.get(Country, attacker_id)
        defender_after = await session.get(Country, defender_id)
        assert attacker_after.treasury == Decimal("1000000") + result.money_looted
        assert defender_after.treasury == Decimal("500000") - result.money_looted


async def test_cannot_attack_self(session_factory):
    from bot.services.combat import CombatError

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
        country_id, world_id = country.id, world.id
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(CombatError):
            await resolve_attack(
                session,
                world_id=world_id,
                attacker_country_id=country_id,
                defender_country_id=country_id,
                category=UnitCategory.GROUND,
                attack_order={},
            )
