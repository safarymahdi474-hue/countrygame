from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import back_to_menu_keyboard
from bot.keyboards.market import (
    ITEM_LABELS,
    back_to_market_keyboard,
    item_choice_keyboard,
    listing_item_keyboard,
    market_menu_keyboard,
    my_listing_item_keyboard,
)
from bot.models.country import Country
from bot.models.market import MarketListing
from bot.models.resources import ResourceType
from bot.services import identity, market, season
from bot.services.market import MarketError
from bot.services.notify import notify_user
from bot.states.market_states import CreateListingStates

router = Router(name="market")


def _parse_item(code: str) -> ResourceType | None:
    return None if code == "money" else ResourceType(code)


async def _current_country(session: AsyncSession, telegram_user) -> Country | None:
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


def _format_listing(listing: MarketListing, seller_name: str) -> str:
    offer_label = ITEM_LABELS["money" if listing.offer_resource is None else listing.offer_resource.value]
    request_label = ITEM_LABELS["money" if listing.request_resource is None else listing.request_resource.value]
    return (
        f"#{listing.id} — {seller_name}\n"
        f"می‌ده: {listing.offer_amount:,.0f} {offer_label}\n"
        f"می‌خواد: {listing.request_amount:,.0f} {request_label}"
    )


@router.callback_query(F.data == "menu:market")
async def on_market_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text("🛒 بازار جهانی:", reply_markup=market_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "mkt:listings")
async def on_listings(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    listings = await market.list_open_listings(
        session, world_id=country.world_id, exclude_seller_id=country.id
    )
    if not listings:
        await callback.answer("فعلاً آگهی بازی نیست.", show_alert=True)
        return

    first = listings[0]
    seller_result = await session.execute(
        select(Country.display_name).where(Country.id == first.seller_country_id)
    )
    seller_name = seller_result.scalar_one_or_none() or "؟"

    other_lines = []
    for listing in listings[1:]:
        s = await session.execute(
            select(Country.display_name).where(Country.id == listing.seller_country_id)
        )
        other_lines.append(_format_listing(listing, s.scalar_one_or_none() or "؟"))

    text = _format_listing(first, seller_name)
    if other_lines:
        text += "\n\n---\n\n" + "\n\n".join(other_lines)
        text += "\n\n(برای خرید بقیه، فعلاً باید شماره‌شون رو به من پیام بدی — این قابلیت فاز بعد کامل می‌شه)"

    await callback.message.edit_text(text, reply_markup=listing_item_keyboard(first))
    await callback.answer()


@router.callback_query(F.data.startswith("mbuy:"))
async def on_buy(callback: CallbackQuery, session: AsyncSession) -> None:
    listing_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    try:
        listing = await market.accept_listing(session, listing_id, country.id)
    except MarketError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await callback.message.edit_text("✅ معامله انجام شد.", reply_markup=back_to_market_keyboard())
    await callback.answer()

    seller_telegram_id = await identity.get_telegram_id_for_country(session, listing.seller_country_id)
    await notify_user(
        callback.bot, seller_telegram_id,
        f"💳 {country.display_name} آگهی #{listing.id} تو رو خرید.",
    )


@router.callback_query(F.data == "mkt:mine")
async def on_my_listings(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    listings = await market.list_my_listings(session, seller_country_id=country.id)
    if not listings:
        await callback.answer("آگهی بازی نداری.", show_alert=True)
        return

    first = listings[0]
    await callback.message.edit_text(
        _format_listing(first, country.display_name), reply_markup=my_listing_item_keyboard(first)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mcancel:"))
async def on_cancel_listing(callback: CallbackQuery, session: AsyncSession) -> None:
    listing_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    try:
        await market.cancel_listing(session, listing_id, country.id)
    except MarketError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.edit_text("🚫 آگهی لغو شد.", reply_markup=back_to_market_keyboard())
    await callback.answer()


@router.callback_query(F.data == "mkt:new")
async def on_new_listing_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text(
        "چی می‌خوای عرضه کنی؟", reply_markup=item_choice_keyboard("moffer")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("moffer:"))
async def on_offer_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await state.update_data(offer_item=code)
    await state.set_state(CreateListingStates.waiting_offer_amount)
    await callback.message.edit_text(f"چقدر {ITEM_LABELS[code]} می‌دی؟ عدد بفرست.")
    await callback.answer()


@router.message(CreateListingStates.waiting_offer_amount)
async def on_offer_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal((message.text or "").strip())
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("یه عدد مثبت معتبر بفرست.")
        return

    await state.update_data(offer_amount=str(amount))
    await state.set_state(None)  # منتظر انتخاب دکمه‌ی بعدی
    await message.answer("در عوض چی می‌خوای؟", reply_markup=item_choice_keyboard("mrequest"))


@router.callback_query(F.data.startswith("mrequest:"))
async def on_request_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    await state.update_data(request_item=code)
    await state.set_state(CreateListingStates.waiting_request_amount)
    await callback.message.edit_text(f"چقدر {ITEM_LABELS[code]} می‌خوای؟ عدد بفرست.")
    await callback.answer()


@router.message(CreateListingStates.waiting_request_amount)
async def on_request_amount(message: Message, session: AsyncSession, state: FSMContext) -> None:
    try:
        request_amount = Decimal((message.text or "").strip())
        if request_amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("یه عدد مثبت معتبر بفرست.")
        return

    data = await state.get_data()
    country = await _current_country(session, message.from_user)
    if country is None:
        await state.clear()
        await message.answer("هنوز کشوری نداری.")
        return

    offer_item = _parse_item(data["offer_item"])
    request_item = _parse_item(data["request_item"])
    offer_amount = Decimal(data["offer_amount"])

    try:
        await market.create_listing(
            session,
            world_id=country.world_id,
            seller_country_id=country.id,
            offer_resource=offer_item,
            offer_amount=offer_amount,
            request_resource=request_item,
            request_amount=request_amount,
        )
    except MarketError as exc:
        await message.answer(f"❌ {exc}")
        return

    await state.clear()
    await message.answer("✅ آگهی ثبت شد.", reply_markup=market_menu_keyboard())
