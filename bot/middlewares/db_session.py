from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.database.engine import session_scope


class DbSessionMiddleware(BaseMiddleware):
    """
    برای هر آپدیت، یک session تازه می‌سازه و بعد از پردازش، commit یا
    rollback خودکار می‌کنه (طبق session_scope). هندلرها فقط کافیه
    آرگومان `session` رو بگیرن، بدون اینکه نگران commit/rollback باشن.
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope(self.session_factory) as session:
            data["session"] = session
            return await handler(event, data)
