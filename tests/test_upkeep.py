from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, ResourceType, User, UnitType, World, WorldStatus
from bot.models.military import CountryUnit
from bot.services.upkeep import run_upkeep_tick
from bot.services.wallet import adjust_balance, get_balance

pytestmark = pytest.mark.asyncio


async def _make_country_with_tanks(session_factory, *, treasury: str, oil: str, quantity: int):
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
        session.add(CountryUnit(country_id=country.id, unit_type=UnitType.TANK, quantity=quantity))
        await adjust_balance(session, country.id, ResourceType.OIL, Decimal(oil))
        country_id = country.id
        await session.commit()
    return country_id


async def test_upkeep_deducts_money_and_can_go_negative(session_factory):
    country_id = await _make_country_with_tanks(
        session_factory, treasury="10", oil="1000000", quantity=10
    )
    # تانک: نگهداری روزانه $78 هر عدد → 10 تانک = $780/روز
    async with session_factory() as session:
        spent = await run_upkeep_tick(session, country_id, elapsed_seconds=86400)
        await session.commit()
        assert spent["money"] == Decimal("780")

    async with session_factory() as session:
        treasury = await get_balance(session, country_id, None)
        assert treasury == Decimal("10") - Decimal("780")  # خزانه منفی رفته — بدهی


async def test_upkeep_resource_clamps_at_zero(session_factory):
    # نفت خیلی کمتر از نیازه — نباید منفی بشه
    country_id = await _make_country_with_tanks(
        session_factory, treasury="1000000", oil="500", quantity=10
    )
    async with session_factory() as session:
        spent = await run_upkeep_tick(session, country_id, elapsed_seconds=86400)
        await session.commit()
        assert spent[ResourceType.OIL.value] == Decimal("500")  # فقط همون مقدار موجود کم شد

    async with session_factory() as session:
        oil = await get_balance(session, country_id, ResourceType.OIL)
        assert oil == Decimal("0")
