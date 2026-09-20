from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.military import (
    CATEGORY_LABELS,
    UNIT_LABELS,
    cancel_quantity_keyboard,
    military_category_keyboard,
    unit_action_keyboard,
    units_in_category_keyboard,
)
from bot.models.military import UNIT_CATEGORY, UNIT_STATS, CountryUnit, UnitCategory, UnitType
from bot.services import identity, season
from bot.services.military import BuildUnitError, build_units, get_capacity
from bot.states.military_states import BuildUnitStates

router = Router(name="military")


async def _current_country(session: AsyncSession, telegram_user):
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


@router.callback_query(F.data == "menu:military")
async def on_military_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text("یه دسته انتخاب کن:", reply_markup=military_category_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("mcat:"))
async def on_category_selected(callback: CallbackQuery, session: AsyncSession) -> None:
    category = UnitCategory(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    used, total = await get_capacity(session, country.id, category)
    await callback.message.edit_text(
        f"{CATEGORY_LABELS[category]}\nظرفیت: {used}/{total}\n\nیه یگان انتخاب کن:",
        reply_markup=units_in_category_keyboard(category),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("munit:"))
async def on_unit_view(callback: CallbackQuery, session: AsyncSession) -> None:
    unit_type = UnitType(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    stats = UNIT_STATS[unit_type]
    result = await session.execute(
        select(CountryUnit).where(
            CountryUnit.country_id == country.id, CountryUnit.unit_type == unit_type
        )
    )
    row = result.scalar_one_or_none()
    owned = row.quantity if row else 0

    resource_lines = "، ".join(
        f"{res.value}: {amt}" for res, amt in stats.build_cost_resources.items()
    ) or "—"

    text = (
        f"⚔️ {UNIT_LABELS[unit_type]}\n"
        f"تعداد فعلی: {owned}\n\n"
        f"هزینه‌ی ساخت هر عدد: ${stats.build_cost_money:,.0f} + {resource_lines}\n"
        f"ظرفیت مصرفی هر عدد: {stats.capacity_slots}\n"
        f"حمله: {stats.attack} | دقت: {stats.accuracy}٪ | فرار: {stats.evasion}٪"
    )
    await callback.message.edit_text(text, reply_markup=unit_action_keyboard(unit_type))
    await callback.answer()


@router.callback_query(F.data.startswith("mbuild:"))
async def on_build_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    unit_type = UnitType(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    await state.update_data(unit_type=unit_type.value, country_id=country.id)
    await state.set_state(BuildUnitStates.waiting_quantity)

    await callback.message.edit_text(
        f"چند تا {UNIT_LABELS[unit_type]} می‌خوای بسازی؟ یه عدد بفرست.",
        reply_markup=cancel_quantity_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "mbuild_cancel")
async def on_build_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "لغو شد.", reply_markup=military_category_keyboard()
    )
    await callback.answer()


@router.message(BuildUnitStates.waiting_quantity)
async def on_quantity_received(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    unit_type = UnitType(data["unit_type"])
    country_id = data["country_id"]

    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("لطفاً یه عدد صحیح مثبت بفرست (یا لغو رو بزن).")
        return

    quantity = int(raw)

    try:
        await build_units(session, country_id, unit_type, quantity)
    except BuildUnitError as exc:
        await message.answer(f"❌ {exc}")
        return

    await state.clear()
    await message.answer(f"✅ {quantity} عدد {UNIT_LABELS[unit_type]} ساخته شد.")
