from decimal import Decimal

import pytest

from bot.models import Country, CountryTier, ResourceType, User, World, WorldStatus
from bot.models.diplomacy import StatementReactionType, TreatyType
from bot.services import diplomacy, market
from bot.services.wallet import adjust_balance, get_balance

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
                      display_name="Italy", tier=CountryTier.STANDARD, treasury=Decimal("100000"))
        c2 = Country(world_id=world.id, owner_id=u2.id, nation_code="FR",
                      display_name="France", tier=CountryTier.STANDARD, treasury=Decimal("50000"))
        session.add_all([c1, c2])
        await session.flush()
        await adjust_balance(session, c1.id, ResourceType.STEEL, Decimal("100"))
        world_id, c1_id, c2_id = world.id, c1.id, c2.id
        await session.commit()
    return world_id, c1_id, c2_id


async def test_market_trade_with_fee(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        listing = await market.create_listing(
            session, world_id=world_id, seller_country_id=c1_id,
            offer_resource=ResourceType.STEEL, offer_amount=Decimal("100"),
            request_resource=None, request_amount=Decimal("5000"),
        )
        await session.commit()
        listing_id = listing.id

    async with session_factory() as session:
        await market.accept_listing(session, listing_id, c2_id)
        await session.commit()

    async with session_factory() as session:
        assert await get_balance(session, c1_id, ResourceType.STEEL) == 0
        assert await get_balance(session, c2_id, ResourceType.STEEL) == 100
        # فروشنده ۲٪ کارمزد بازار (غیر VIP) می‌ده
        expected_seller_money = Decimal("100000") + Decimal("5000") * Decimal("0.98")
        assert await get_balance(session, c1_id, None) == expected_seller_money
        assert await get_balance(session, c2_id, None) == Decimal("45000")


async def test_treaty_lifecycle(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        treaty = await diplomacy.propose_treaty(
            session, world_id=world_id, proposer_country_id=c1_id,
            target_country_id=c2_id, treaty_type=TreatyType.NON_AGGRESSION,
        )
        await session.commit()
        treaty_id = treaty.id

    async with session_factory() as session:
        treaty = await diplomacy.respond_to_treaty(
            session, treaty_id=treaty_id, responder_country_id=c2_id, accept=True
        )
        await session.commit()
        assert treaty.status.value == "active"


async def test_statement_reactions(session_factory):
    world_id, c1_id, c2_id = await _make_two_countries(session_factory)

    async with session_factory() as session:
        statement = await diplomacy.post_statement(
            session, world_id=world_id, author_country_id=c1_id,
            title="بیانیه تست", body="این یک بیانیه‌ی تستیه.",
        )
        await session.commit()
        statement_id = statement.id

    async with session_factory() as session:
        await diplomacy.react_to_statement(
            session, statement_id=statement_id, country_id=c2_id,
            reaction=StatementReactionType.SUPPORT,
        )
        await session.commit()

    async with session_factory() as session:
        counts = await diplomacy.statement_counts(session, statement_id)
        assert counts[StatementReactionType.SUPPORT] == 1
        assert counts[StatementReactionType.CONDEMN] == 0
