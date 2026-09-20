from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import (
    NATION_CHOICES,
    main_menu_keyboard,
    nation_selection_keyboard,
    switch_country_keyboard,
    tier_selection_keyboard,
    world_selection_keyboard,
)
from bot.models.country import Country, CountryTier
from bot.services import identity, season
from bot.services.identity import IdentityError

router = Router(name="start")


async def _show_country_selection(message_or_callback_message, session: AsyncSession, *, edit: bool) -> None:
    """اگه چند دنیای فعال باشه اول دنیا رو می‌پرسه، وگرنه مستقیم می‌ره سراغ انتخاب کشور."""
    worlds = await season.list_active_worlds(session)
    if not worlds:
        worlds = [await season.get_or_create_active_world(session)]

    if len(worlds) == 1:
        text = "به بازی خوش اومدی! 🌍\nاول باید یه کشور انتخاب کنی:"
        markup = nation_selection_keyboard(worlds[0].id)
    else:
        text = "چند دنیای فعال هست — اول یکی رو انتخاب کن:"
        markup = world_selection_keyboard(worlds)

    if edit:
        await message_or_callback_message.edit_text(text, reply_markup=markup)
    else:
        await message_or_callback_message.answer(text, reply_markup=markup)


async def _send_dashboard_prompt(message: Message, session: AsyncSession) -> None:
    """اگه کاربر کشور داره نشونش بده؛ اگه چندتا داره بذار انتخاب کنه؛ وگرنه بفرستش سراغ ساخت کشور."""
    user = await identity.get_or_create_user(
        session, telegram_id=message.from_user.id, username=message.from_user.username
    )
    countries = await identity.list_countries_for_user(session, user_id=user.id)

    if not countries:
        await _show_country_selection(message, session, edit=False)
        return

    if len(countries) > 1:
        await message.answer(
            "چند تا کشور داری — کدوم رو می‌خوای مدیریت کنی؟",
            reply_markup=switch_country_keyboard(countries),
        )
        return

    country = countries[0]
    await identity.set_current_world(session, user.id, country.world_id)
    await message.answer(
        f"خوش برگشتی، {country.display_name}! 🏛\nخزانه: ${country.treasury:,.0f}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    await _send_dashboard_prompt(message, session)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🎮 راهنمای بازی:\n\n"
        "از منوی اصلی می‌تونی:\n"
        "📊 وضعیت کشورت رو ببینی\n"
        "🏗 ساختمان بسازی/ارتقا بدی\n"
        "🪖 ارتش بسازی\n"
        "⚔️ به کشورهای دیگه حمله کنی\n"
        "🤝 پیمان ببندی و بیانیه بدی\n"
        "🛒 تو بازار جهانی معامله کنی\n"
        "🚧 مرزهات رو باز/بسته کنی\n"
        "🌍 رتبه‌بندی دنیا رو ببینی\n\n"
        "اگه تو چند دنیا کشور داری، از دکمه‌ی «تعویض کشور» تو منو استفاده کن.\n"
        "برای شروع، /start رو بزن."
    )


@router.callback_query(F.data.startswith("pick_world:"))
async def on_pick_world(callback: CallbackQuery, session: AsyncSession) -> None:
    world_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "یه کشور انتخاب کن:", reply_markup=nation_selection_keyboard(world_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pick_nation:"))
async def on_pick_nation(callback: CallbackQuery, session: AsyncSession) -> None:
    _, world_id_raw, nation_code = callback.data.split(":")
    world_id = int(world_id_raw)
    match = next((n for n in NATION_CHOICES if n[0] == nation_code), None)
    if match is None:
        await callback.answer("این گزینه معتبر نیست.", show_alert=True)
        return
    _, flag, display_name = match

    await callback.message.edit_text(
        f"{flag} {display_name} — چه سطحی شروع کنی؟",
        reply_markup=tier_selection_keyboard(world_id, nation_code),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:pick_nation_back:"))
async def on_pick_nation_back(callback: CallbackQuery, session: AsyncSession) -> None:
    world_id = int(callback.data.split(":", 2)[2])
    await callback.message.edit_text(
        "یه کشور انتخاب کن:", reply_markup=nation_selection_keyboard(world_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("nations_page:"))
async def on_nations_page(callback: CallbackQuery, session: AsyncSession) -> None:
    _, world_id_raw, page_raw = callback.data.split(":")
    world_id, page = int(world_id_raw), int(page_raw)
    await callback.message.edit_text(
        "یه کشور انتخاب کن:", reply_markup=nation_selection_keyboard(world_id, page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pick_tier:"))
async def on_pick_tier(callback: CallbackQuery, session: AsyncSession) -> None:
    _, world_id_raw, nation_code, tier_raw = callback.data.split(":")
    world_id = int(world_id_raw)
    match = next((n for n in NATION_CHOICES if n[0] == nation_code), None)
    if match is None:
        await callback.answer("این گزینه معتبر نیست.", show_alert=True)
        return
    _, flag, display_name = match
    tier = CountryTier(tier_raw)

    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )

    try:
        country = await identity.create_country(
            session,
            user_id=user.id,
            world_id=world_id,
            nation_code=nation_code,
            display_name=display_name,
            tier=tier,
        )
    except IdentityError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await identity.set_current_world(session, user.id, world_id)

    await callback.message.edit_text(
        f"{flag} کشور {country.display_name} تأسیس شد!\nخزانه‌ی اولیه: ${country.treasury:,.0f}",
    )
    await callback.message.answer("منوی اصلی:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("switch_country:"))
async def on_switch_country(callback: CallbackQuery, session: AsyncSession) -> None:
    country_id = int(callback.data.split(":", 1)[1])
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    country = await session.get(Country, country_id)
    if country is None or country.owner_id != user.id:
        await callback.answer("این کشور مال تو نیست.", show_alert=True)
        return

    await identity.set_current_world(session, user.id, country.world_id)
    await callback.message.edit_text(
        f"{country.display_name} 🏛\nخزانه: ${country.treasury:,.0f}",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:switch_country")
async def on_switch_country_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    countries = await identity.list_countries_for_user(session, user_id=user.id)
    if len(countries) <= 1:
        await callback.answer("فقط یه کشور داری.", show_alert=True)
        return
    await callback.message.edit_text(
        "کدوم کشور؟", reply_markup=switch_country_keyboard(countries)
    )
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def on_back_to_main(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    country = await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text(
        f"{country.display_name} 🏛\nخزانه: ${country.treasury:,.0f}",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
