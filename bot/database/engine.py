"""
راه‌اندازی SQLAlchemy async engine و session factory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# نام‌گذاریِ ثابت برای همه‌ی constraint ها — بدون این، Alembic موقع
# autogenerate برای drop_constraint نمی‌تونه اسم دقیق بسازه (مخصوصاً رو
# SQLite) و مایگریشن downgrade می‌شکنه.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """کلاس پایه‌ی همه‌ی مدل‌های ORM."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """
    Context manager برای هندل کردن تراکنش‌ها:
    - commit خودکار در صورت موفقیت
    - rollback خودکار در صورت خطا
    استفاده‌ش تو کل پروژه یکسان می‌مونه تا هیچ‌جا تراکنش نیمه‌کاره نمونه.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
