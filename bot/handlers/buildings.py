from __future__ import annotations

from sqlalchemy import select

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.buildings import (
    BUILDING_LABELS,
    CATEGORY_LABELS,
    building_action_keyboard,
    buildings_in_category_keyboard,
    category_menu_keyboard,
)
from bot.models.buildings import (
    BUILDING_CATEGORY,
    MAX_BUILDING_LEVEL,
    BuildingCategory,
    BuildingType,
    CountryBuilding,
)
from bot.services import identity, season
from bot.services.construction import ConstructionError, upgrade_building
from bot.services.economy import upgrade_cost

router = Router(name="buildings")


async def _current_country(session: AsyncSession, telegram_user):
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


@router.callback_query(F.data == "menu:buildings")
async def on_buildings_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text("یه دسته انتخاب کن:", reply_markup=category_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("bcat:"))
async def on_category_selected(callback: CallbackQuery, session: AsyncSession) -> None:
    category = BuildingCategory(callback.data.split(":", 1)[1])
    buildings = [bt for bt, cat in BUILDING_CATEGORY.items() if cat == category]
    await callback.message.edit_text(
        f"{CATEGORY_LABELS[category]} — یکی رو انتخاب کن:",
        reply_markup=buildings_in_category_keyboard(buildings),
    )
    await callback.answer()


async def _render_building_view(callback: CallbackQuery, session: AsyncSession, building_type: BuildingType, country) -> None:
    result = await session.execute(
        select(CountryBuilding).where(
            CountryBuilding.country_id == country.id,
            CountryBuilding.building_type == building_type,
        )
    )
    row = result.scalar_one_or_none()
    current_level = row.level if row else 0

    text = f"🏗 {BUILDING_LABELS[building_type]}\nسطح فعلی: {current_level}/{MAX_BUILDING_LEVEL}\n"
    if current_level >= MAX_BUILDING_LEVEL:
        text += "\nبه سقف سطح رسیده."
    else:
        cost = upgrade_cost(building_type, current_level + 1)
        text += f"\nهزینه‌ی ارتقا به سطح {current_level + 1}: ${cost:,.0f}"

    await callback.message.edit_text(text, reply_markup=building_action_keyboard(building_type))


@router.callback_query(F.data.startswith("bview:"))
async def on_building_view(callback: CallbackQuery, session: AsyncSession) -> None:
    building_type = BuildingType(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    await _render_building_view(callback, session, building_type, country)
    await callback.answer()


@router.callback_query(F.data.startswith("bupgrade:"))
async def on_building_upgrade(callback: CallbackQuery, session: AsyncSession) -> None:
    building_type = BuildingType(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    try:
        building = await upgrade_building(session, country.id, building_type)
    except ConstructionError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await _render_building_view(callback, session, building_type, country)
    await callback.answer(f"✅ سطح جدید: {building.level}")
