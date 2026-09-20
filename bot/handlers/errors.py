from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    """
    هر استثنای هندل‌نشده تو کل ربات از اینجا رد می‌شه — به‌جای کرش کردن
    پولینگ، لاگ می‌شه و (در حد امکان) یه پیام خطای عمومی به کاربر می‌ره.
    """
    logger.exception("خطای هندل‌نشده در آپدیت %s", event.update, exc_info=event.exception)

    update = event.update
    try:
        if update.message is not None:
            await update.message.answer("⚠️ یه خطای داخلی پیش اومد. لطفاً دوباره امتحان کن.")
        elif update.callback_query is not None:
            await update.callback_query.answer("⚠️ خطای داخلی — دوباره امتحان کن.", show_alert=True)
    except Exception:
        logger.warning("ارسال پیام خطا به کاربر هم ناموفق بود.", exc_info=True)

    return True
