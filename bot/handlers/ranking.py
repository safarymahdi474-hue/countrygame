from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import back_to_menu_keyboard
from bot.models.country import Country
from bot.services import achievements, identity, ranking, scoring, season

router = Router(name="ranking")


@router.callback_query(F.data == "menu:ranking")
async def on_ranking(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    my_country = await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)
    if my_country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    # قبل از رتبه‌بندی، امتیاز همه‌ی کشورهای دنیا رو تازه می‌کنیم
    result = await session.execute(select(Country.id).where(Country.world_id == world.id))
    for (country_id,) in result.all():
        await scoring.recompute_scores(session, country_id)

    leaderboard = await ranking.compute_leaderboard(session, world.id)

    id_to_name: dict[int, str] = {}
    names_result = await session.execute(
        select(Country.id, Country.display_name).where(Country.world_id == world.id)
    )
    for cid, name in names_result.all():
        id_to_name[cid] = name

    lines = [f"🌍 رتبه‌بندی {world.name}", ""]
    my_rank: int | None = None
    for idx, entry in enumerate(leaderboard[:10], start=1):
        marker = "👑 " if idx == 1 else f"{idx}. "
        lines.append(f"{marker}{id_to_name.get(entry.country_id, '?')} — {entry.overall_score:,.1f}")
        if entry.country_id == my_country.id:
            my_rank = idx

    if my_rank is None:
        for idx, entry in enumerate(leaderboard, start=1):
            if entry.country_id == my_country.id:
                my_rank = idx
                break
        if my_rank is not None:
            lines += ["", f"رتبه‌ی تو: {my_rank}ام"]

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:achievements")
async def on_achievements(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    country = await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    items = await achievements.list_achievements(session, country.id)
    if not items:
        text = "🏆 هنوز دستاوردی نداری — فصل رو با رتبه‌ی بالا تموم کن!"
    else:
        lines = [f"🏆 دستاوردهای {country.display_name}:\n"]
        for a in items:
            lines.append(f"• {a.title} — {a.description}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
