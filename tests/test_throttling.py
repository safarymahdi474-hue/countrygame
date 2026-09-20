import asyncio
from types import SimpleNamespace

import pytest

from bot.middlewares.throttling import ThrottlingMiddleware


class FakeUser:
    def __init__(self, id_: int):
        self.id = id_


class FakeMessage:
    def __init__(self, user_id: int):
        self.from_user = FakeUser(user_id)


@pytest.mark.asyncio
async def test_second_rapid_call_is_dropped():
    middleware = ThrottlingMiddleware(interval_seconds=1.0)
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "ok"

    msg = FakeMessage(user_id=1)
    result1 = await middleware(handler, msg, {})
    result2 = await middleware(handler, msg, {})  # بلافاصله بعدی — باید نادیده گرفته بشه

    assert result1 == "ok"
    assert result2 is None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_calls_after_interval_pass_through():
    middleware = ThrottlingMiddleware(interval_seconds=0.05)
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "ok"

    msg = FakeMessage(user_id=2)
    await middleware(handler, msg, {})
    await asyncio.sleep(0.1)
    await middleware(handler, msg, {})

    assert len(calls) == 2


@pytest.mark.asyncio
async def test_different_users_are_independent():
    middleware = ThrottlingMiddleware(interval_seconds=1.0)
    calls = []

    async def handler(event, data):
        calls.append(event)
        return "ok"

    await middleware(handler, FakeMessage(user_id=10), {})
    await middleware(handler, FakeMessage(user_id=20), {})

    assert len(calls) == 2
