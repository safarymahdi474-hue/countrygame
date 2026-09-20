import datetime as dt
from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, ResourceType, User, World, WorldStatus
from bot.services import ledger
from bot.services.wallet import adjust_balance

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
                           display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("100000"))
        session.add(country)
        await session.flush()
        country_id = country.id
        await session.commit()
    return country_id


async def test_adjust_balance_records_ledger_entry(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        await adjust_balance(session, country_id, None, Decimal("5000"), source="test:income")
        await adjust_balance(session, country_id, None, Decimal("-2000"), source="test:expense")
        await session.commit()

    async with session_factory() as session:
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        summary = await ledger.summary_since(session, country_id, since=since)
        from bot.models.ledger import LedgerItem
        assert summary[LedgerItem.MONEY]["income"] == Decimal("5000")
        assert summary[LedgerItem.MONEY]["expense"] == Decimal("2000")
        assert summary[LedgerItem.MONEY]["net"] == Decimal("3000")


async def test_power_adjustments_are_not_logged(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        await adjust_balance(session, country_id, ResourceType.POWER, Decimal("100"), source="test:power")
        await session.commit()

    async with session_factory() as session:
        entries = await ledger.recent_entries(session, country_id)
        assert entries == []


async def test_zero_delta_not_logged(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        await ledger.record_entry(session, country_id=country_id, item=None, delta=Decimal("0"), source="noop")
        await session.commit()

    async with session_factory() as session:
        entries = await ledger.recent_entries(session, country_id)
        assert entries == []


async def test_recent_entries_ordering(session_factory):
    country_id = await _make_country(session_factory)

    async with session_factory() as session:
        await adjust_balance(session, country_id, None, Decimal("100"), source="a")
        await adjust_balance(session, country_id, None, Decimal("200"), source="b")
        await session.commit()

    async with session_factory() as session:
        entries = await ledger.recent_entries(session, country_id, limit=10)
        assert len(entries) == 2
        # جدیدترین اول
        assert entries[0].source == "b"
        assert entries[1].source == "a"
