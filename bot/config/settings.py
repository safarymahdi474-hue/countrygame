"""
تنظیمات کلی پروژه.
همه مقادیر حساس (توکن، دیتابیس) از متغیرهای محیطی خونده می‌شن؛
هیچ‌وقت مستقیم تو کد نوشته نمی‌شن.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    database_url: str  # مثال: postgresql+asyncpg://user:pass@host:5432/dbname
    admin_ids: tuple[int, ...]
    debug: bool = False

    # --- تنظیمات زمان‌بندی و اقتصاد پایه ---
    # این‌ها فعلاً placeholder هستن؛ فاز ۲ (اقتصاد) دقیق‌ترشون می‌کنیم.
    tick_interval_seconds: int = 60  # هر چند وقت یک‌بار موتور اقتصادی محاسبه می‌شه
    season_length_days: int = 45

    # --- مانیتورینگ (اختیاری) ---
    sentry_dsn: str | None = None


def normalize_database_url(url: str) -> str:
    """
    Railway (و خیلی سرویس‌های دیگه) معمولاً DATABASE_URL رو به‌صورت
    postgresql:// یا postgres:// می‌دن (درایور sync پیش‌فرض). این پروژه
    فقط asyncpg نصب داره، پس همیشه درایور رو asyncpg اجبار می‌کنیم —
    دیگه لازم نیست دستی تو env این رو درست کنی.
    """
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def load_settings() -> Settings:
    token = os.environ.get("BOT_TOKEN")
    db_url = os.environ.get("DATABASE_URL")
    if not token:
        raise RuntimeError("BOT_TOKEN تنظیم نشده — متغیر محیطی رو ست کن.")
    if not db_url:
        raise RuntimeError("DATABASE_URL تنظیم نشده — متغیر محیطی رو ست کن.")

    raw_admins = os.environ.get("ADMIN_IDS", "")
    admin_ids = tuple(int(x) for x in raw_admins.split(",") if x.strip())

    return Settings(
        bot_token=token,
        database_url=normalize_database_url(db_url),
        admin_ids=admin_ids,
        debug=os.environ.get("DEBUG", "0") == "1",
        sentry_dsn=os.environ.get("SENTRY_DSN") or None,
    )
