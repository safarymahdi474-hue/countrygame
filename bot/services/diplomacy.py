from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.diplomacy import (
    BorderStatus,
    CountryBorderPolicy,
    Statement,
    StatementReaction,
    StatementReactionType,
    Treaty,
    TreatyStatus,
    TreatyType,
)


class DiplomacyError(Exception):
    pass


async def propose_treaty(
    session: AsyncSession,
    *,
    world_id: int,
    proposer_country_id: int,
    target_country_id: int,
    treaty_type: TreatyType,
) -> Treaty:
    if proposer_country_id == target_country_id:
        raise DiplomacyError("نمی‌تونی با خودت پیمان ببندی.")

    # ترتیب رو ثابت می‌کنیم (کوچیک‌تر همیشه country_a) تا UniqueConstraint
    # مستقل از اینکه کی پیشنهاد داده درست کار کنه.
    country_a_id, country_b_id = sorted((proposer_country_id, target_country_id))

    existing = await session.execute(
        select(Treaty).where(
            Treaty.world_id == world_id,
            Treaty.country_a_id == country_a_id,
            Treaty.country_b_id == country_b_id,
            Treaty.treaty_type == treaty_type,
            Treaty.status.in_([TreatyStatus.PENDING, TreatyStatus.ACTIVE]),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise DiplomacyError("پیمانی از همین نوع بین این دو کشور از قبل هست.")

    treaty = Treaty(
        world_id=world_id,
        country_a_id=country_a_id,
        country_b_id=country_b_id,
        proposed_by_id=proposer_country_id,
        treaty_type=treaty_type,
        status=TreatyStatus.PENDING,
    )
    session.add(treaty)
    return treaty


async def respond_to_treaty(
    session: AsyncSession, *, treaty_id: int, responder_country_id: int, accept: bool
) -> Treaty:
    result = await session.execute(select(Treaty).where(Treaty.id == treaty_id))
    treaty = result.scalar_one_or_none()
    if treaty is None:
        raise DiplomacyError("پیمان پیدا نشد.")
    if treaty.status != TreatyStatus.PENDING:
        raise DiplomacyError("این پیمان دیگه در انتظار پاسخ نیست.")
    if treaty.proposed_by_id == responder_country_id:
        raise DiplomacyError("پیشنهاددهنده نمی‌تونه به پیشنهاد خودش پاسخ بده.")
    if responder_country_id not in (treaty.country_a_id, treaty.country_b_id):
        raise DiplomacyError("این پیمان به کشور تو مربوط نیست.")

    treaty.status = TreatyStatus.ACTIVE if accept else TreatyStatus.REJECTED
    treaty.responded_at = dt.datetime.now(dt.timezone.utc)
    return treaty


async def cancel_treaty(
    session: AsyncSession, *, treaty_id: int, requester_country_id: int
) -> Treaty:
    result = await session.execute(select(Treaty).where(Treaty.id == treaty_id))
    treaty = result.scalar_one_or_none()
    if treaty is None:
        raise DiplomacyError("پیمان پیدا نشد.")
    if requester_country_id not in (treaty.country_a_id, treaty.country_b_id):
        raise DiplomacyError("این پیمان به کشور تو مربوط نیست.")
    if treaty.status != TreatyStatus.ACTIVE:
        raise DiplomacyError("فقط پیمان فعال قابل لغوه.")

    treaty.status = TreatyStatus.CANCELLED
    return treaty


async def post_statement(
    session: AsyncSession, *, world_id: int, author_country_id: int, title: str, body: str
) -> Statement:
    if not title.strip() or not body.strip():
        raise DiplomacyError("عنوان و متن بیانیه نمی‌تونه خالی باشه.")
    statement = Statement(
        world_id=world_id, author_country_id=author_country_id, title=title.strip(), body=body.strip()
    )
    session.add(statement)
    return statement


async def react_to_statement(
    session: AsyncSession,
    *,
    statement_id: int,
    country_id: int,
    reaction: StatementReactionType,
) -> StatementReaction:
    result = await session.execute(
        select(StatementReaction).where(
            StatementReaction.statement_id == statement_id,
            StatementReaction.country_id == country_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.reaction = reaction  # می‌تونه نظرش رو عوض کنه
        return existing

    row = StatementReaction(statement_id=statement_id, country_id=country_id, reaction=reaction)
    session.add(row)
    return row


async def statement_counts(
    session: AsyncSession, statement_id: int
) -> dict[StatementReactionType, int]:
    result = await session.execute(
        select(StatementReaction.reaction).where(StatementReaction.statement_id == statement_id)
    )
    counts = {StatementReactionType.SUPPORT: 0, StatementReactionType.CONDEMN: 0}
    for (reaction,) in result.all():
        counts[reaction] += 1
    return counts


async def list_pending_treaties_for(session: AsyncSession, country_id: int) -> list[Treaty]:
    """پیمان‌هایی که یکی دیگه به این کشور پیشنهاد داده و هنوز پاسخ نداده."""
    result = await session.execute(
        select(Treaty).where(
            Treaty.status == TreatyStatus.PENDING,
            Treaty.proposed_by_id != country_id,
            (Treaty.country_a_id == country_id) | (Treaty.country_b_id == country_id),
        )
    )
    return list(result.scalars().all())


async def list_active_treaties_for(session: AsyncSession, country_id: int) -> list[Treaty]:
    result = await session.execute(
        select(Treaty).where(
            Treaty.status == TreatyStatus.ACTIVE,
            (Treaty.country_a_id == country_id) | (Treaty.country_b_id == country_id),
        )
    )
    return list(result.scalars().all())


async def list_recent_statements(
    session: AsyncSession, world_id: int, *, limit: int = 10
) -> list[Statement]:
    result = await session.execute(
        select(Statement)
        .where(Statement.world_id == world_id)
        .order_by(Statement.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


BORDER_FIELDS = ("ground_status", "air_status", "naval_status", "trade_status")


async def get_or_create_border_policy(
    session: AsyncSession, country_id: int
) -> CountryBorderPolicy:
    result = await session.execute(
        select(CountryBorderPolicy).where(CountryBorderPolicy.country_id == country_id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = CountryBorderPolicy(country_id=country_id)
        session.add(policy)
        await session.flush()
    return policy


async def set_border_status(
    session: AsyncSession, country_id: int, border: str, status: BorderStatus
) -> CountryBorderPolicy:
    if border not in BORDER_FIELDS:
        raise DiplomacyError("نوع مرز نامعتبره.")
    policy = await get_or_create_border_policy(session, country_id)
    setattr(policy, border, status)
    return policy
