from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """
    محدودسازی ساده‌ی نرخ درخواست — هر کاربر حداکثر یه پیام/کلیک در
    `interval` ثانیه. درون‌حافظه‌ایه (کافیه برای یک instance؛ اگه بعداً
    چند worker موازی داشتیم، باید بره رو Redis).
    """

    def __init__(self, interval_seconds: float = 0.4) -> None:
        self.interval = interval_seconds
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)

        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id)
            if last is not None and (now - last) < self.interval:
                # درخواست رو بی‌سروصدا نادیده می‌گیریم — نه خطا، فقط اسپم رو کند می‌کنیم
                if isinstance(event, CallbackQuery):
                    await event.answer()
                return None
            self._last_seen[user.id] = now

        return await handler(event, data)
