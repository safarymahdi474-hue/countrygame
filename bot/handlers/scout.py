from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.combat import scout_target_keyboard, war_category_keyboard
from bot.models.buildings import BuildingType, CountryBuilding
from bot.models.country import Country
from bot.services import identity, scoring, season

router = Router(name="scout")


async def _current_country(session: AsyncSession, telegram_user) -> Country | None:
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


@router.callback_query(F.data == "scout:menu")
async def on_scout_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    result = await session.execute(
        select(CountryBuilding.level).where(
            CountryBuilding.country_id == country.id,
            CountryBuilding.building_type == BuildingType.SPACE_CENTER,
        )
    )
    space_center_level = result.scalar_one_or_none() or 0
    if space_center_level <= 0:
        await callback.answer("اول باید مرکز فضایی بسازی.", show_alert=True)
        return

    targets = await identity.list_other_countries(
        session, world_id=country.world_id, exclude_country_id=country.id
    )
    if not targets:
        await callback.answer("کشور دیگه‌ای نیست.", show_alert=True)
        return

    await callback.message.edit_text(
        "🛰 کدوم کشور رو شناسایی کنم؟", reply_markup=scout_target_keyboard(targets)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ascout:"))
async def on_scout_target(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    target = await scoring.recompute_scores(session, target_id)

    text = (
        f"🛰 گزارش شناسایی: {target.display_name}\n\n"
        f"📊 اقتصادی: {target.score_economic:,.0f}\n"
        f"🪖 نظامی: {target.score_military:,.0f}\n"
        f"🗺 قلمرو: {target.score_territory:,.0f}\n"
        f"🏗 توسعه: {target.score_development:,.0f}\n"
        f"🤝 دیپلماسی: {target.score_diplomacy:,.0f}"
    )
    await callback.message.edit_text(text, reply_markup=war_category_keyboard())
    await callback.answer()
