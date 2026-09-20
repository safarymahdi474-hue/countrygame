from __future__ import annotations

import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


async def notify_user(bot: Bot, telegram_id: int | None, text: str) -> None:
    """
    تلاش برای فرستادن پیام به یه کاربر (مثلاً اطلاع حمله یا پیشنهاد پیمان).
    اگه کاربر بات رو بلاک کرده باشه یا هر خطای دیگه‌ای پیش بیاد، فقط لاگ
    می‌کنیم — نباید کل عملیات اصلی (حمله، پیمان و ...) به خاطر این شکست بخوره.
    """
    if telegram_id is None:
        return
    try:
        await bot.send_message(telegram_id, text)
    except Exception:
        logger.warning("ارسال اعلان به %s ناموفق بود", telegram_id, exc_info=True)
