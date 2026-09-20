from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.borders import STATUS_CYCLE, borders_menu_keyboard
from bot.models.country import Country
from bot.services import diplomacy, identity, season
from bot.services.diplomacy import DiplomacyError

router = Router(name="borders")


async def _current_country(session: AsyncSession, telegram_user) -> Country | None:
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


@router.callback_query(F.data == "menu:borders")
async def on_borders_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    policy = await diplomacy.get_or_create_border_policy(session, country.id)
    await callback.message.edit_text(
        "🚧 مرزهای کشورت — برای تغییر روی هرکدوم بزن:",
        reply_markup=borders_menu_keyboard(policy),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("border:"))
async def on_border_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    field = callback.data.split(":", 1)[1]
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    policy = await diplomacy.get_or_create_border_policy(session, country.id)
    current_status = getattr(policy, field)
    new_status = STATUS_CYCLE[current_status]

    try:
        policy = await diplomacy.set_border_status(session, country.id, field, new_status)
    except DiplomacyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.message.edit_text(
        "🚧 مرزهای کشورت — برای تغییر روی هرکدوم بزن:",
        reply_markup=borders_menu_keyboard(policy),
    )
    await callback.answer(f"تغییر کرد به {new_status.value}")
