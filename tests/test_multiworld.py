from decimal import Decimal

import pytest

from bot.models import User, World, WorldStatus
from bot.services import identity, season

pytestmark = pytest.mark.asyncio


async def test_list_and_create_multiple_worlds(session_factory):
    async with session_factory() as session:
        w1 = await season.create_world(session, name="World 1", season_length_days=30)
        w2 = await season.create_world(session, name="World 2", season_length_days=20)
        await session.commit()
        w1_id, w2_id = w1.id, w2.id

    async with session_factory() as session:
        worlds = await season.list_active_worlds(session)
        ids = {w.id for w in worlds}
        assert w1_id in ids and w2_id in ids


async def test_cannot_create_duplicate_world_name(session_factory):
    async with session_factory() as session:
        await season.create_world(session, name="Same Name")
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(season.SeasonError):
            await season.create_world(session, name="Same Name")


async def test_get_active_world_for_user_respects_current_world(session_factory):
    async with session_factory() as session:
        w1 = await season.create_world(session, name="World A")
        w2 = await season.create_world(session, name="World B")
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        w1_id, w2_id, user_id = w1.id, w2.id, user.id
        await session.commit()

    async with session_factory() as session:
        user = await session.get(User, user_id)
        world = await identity.get_active_world_for_user(session, user)
        # هنوز current_world_id ست نشده — باید یکی از دنیاهای فعال رو بده و ثبتش کنه
        assert world.id in (w1_id, w2_id)
        assert user.current_world_id == world.id
        await session.commit()

    async with session_factory() as session:
        await identity.set_current_world(session, user_id, w2_id)
        await session.commit()

    async with session_factory() as session:
        user = await session.get(User, user_id)
        world = await identity.get_active_world_for_user(session, user)
        assert world.id == w2_id


async def test_list_countries_for_user_across_worlds(session_factory):
    from decimal import Decimal as D
    from bot.models import Country, CountryTier

    async with session_factory() as session:
        w1 = await season.create_world(session, name="World X")
        w2 = await season.create_world(session, name="World Y")
        await session.flush()
        user = User(telegram_id=1, username="a")
        session.add(user)
        await session.flush()
        c1 = Country(world_id=w1.id, owner_id=user.id, nation_code="IT",
                      display_name="Italy", tier=CountryTier.STANDARD, treasury=D("0"))
        c2 = Country(world_id=w2.id, owner_id=user.id, nation_code="FR",
                      display_name="France", tier=CountryTier.STANDARD, treasury=D("0"))
        session.add_all([c1, c2])
        await session.flush()
        user_id = user.id
        await session.commit()

    async with session_factory() as session:
        countries = await identity.list_countries_for_user(session, user_id=user_id)
        assert len(countries) == 2
        assert {c.nation_code for c in countries} == {"IT", "FR"}
