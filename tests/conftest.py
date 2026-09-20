from __future__ import annotations

import pytest
import pytest_asyncio

from bot.database.engine import Base, build_engine, build_session_factory


@pytest_asyncio.fixture
async def session_factory():
    """
    برای هر تست یه دیتابیس SQLite درون‌حافظه‌ای تازه می‌سازه — تست‌ها
    کاملاً از هم ایزوله‌ان و نیازی به دیتابیس واقعی نیست.
    """
    engine = build_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = build_session_factory(engine)
    yield factory
    await engine.dispose()
