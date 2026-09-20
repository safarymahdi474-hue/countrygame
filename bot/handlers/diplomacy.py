from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.diplomacy import (
    TREATY_TYPE_LABELS,
    active_treaty_keyboard,
    diplomacy_menu_keyboard,
    pending_treaty_keyboard,
    statement_action_keyboard,
    statements_menu_keyboard,
    treaty_target_keyboard,
    treaty_type_keyboard,
)
from bot.keyboards.main_menu import back_to_menu_keyboard
from bot.models.country import Country
from bot.models.diplomacy import StatementReactionType, TreatyType
from bot.services import diplomacy, identity, season
from bot.services.diplomacy import DiplomacyError
from bot.services.notify import notify_user
from bot.states.diplomacy_states import StatementStates

router = Router(name="diplomacy")


async def _current_country(session: AsyncSession, telegram_user) -> Country | None:
    user = await identity.get_or_create_user(
        session, telegram_id=telegram_user.id, username=telegram_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    return await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)


async def _country_name(session: AsyncSession, country_id: int) -> str:
    result = await session.execute(select(Country.display_name).where(Country.id == country_id))
    return result.scalar_one_or_none() or "؟"


@router.callback_query(F.data == "menu:diplomacy")
async def on_diplomacy_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await callback.message.edit_text("بخش دیپلماسی:", reply_markup=diplomacy_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "dip:propose")
async def on_propose_start(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    targets = await identity.list_other_countries(
        session, world_id=country.world_id, exclude_country_id=country.id
    )
    if not targets:
        await callback.answer("کشور دیگه‌ای نیست.", show_alert=True)
        return
    await callback.message.edit_text(
        "با کدوم کشور می‌خوای پیمان ببندی؟", reply_markup=treaty_target_keyboard(targets)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tpropose:"))
async def on_propose_target(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id = int(callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        "چه نوع پیمانی؟", reply_markup=treaty_type_keyboard(target_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ttype:"))
async def on_propose_type(callback: CallbackQuery, session: AsyncSession) -> None:
    _, type_raw, target_id_raw = callback.data.split(":")
    treaty_type = TreatyType(type_raw)
    target_id = int(target_id_raw)

    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    try:
        await diplomacy.propose_treaty(
            session,
            world_id=country.world_id,
            proposer_country_id=country.id,
            target_country_id=target_id,
            treaty_type=treaty_type,
        )
    except DiplomacyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    target_name = await _country_name(session, target_id)
    await callback.message.edit_text(
        f"✅ پیشنهاد {TREATY_TYPE_LABELS[treaty_type]} برای {target_name} ارسال شد.",
        reply_markup=diplomacy_menu_keyboard(),
    )
    await callback.answer()

    target_telegram_id = await identity.get_telegram_id_for_country(session, target_id)
    await notify_user(
        callback.bot, target_telegram_id,
        f"🤝 {country.display_name} پیشنهاد {TREATY_TYPE_LABELS[treaty_type]} بهت داده — "
        "از منوی دیپلماسی، «پیمان‌های در انتظار» رو چک کن.",
    )


@router.callback_query(F.data == "dip:pending")
async def on_pending_treaties(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    pending = await diplomacy.list_pending_treaties_for(session, country.id)
    if not pending:
        await callback.answer("پیمانی در انتظار نداری.", show_alert=True)
        return

    lines = ["📥 پیمان‌های در انتظار پاسخ:\n"]
    for t in pending:
        other_id = t.country_a_id if t.country_a_id != country.id else t.country_b_id
        other_name = await _country_name(session, other_id)
        lines.append(f"#{t.id} — {TREATY_TYPE_LABELS[t.treaty_type]} از طرف {other_name}")

    # فقط اولین مورد رو با دکمه نشون می‌دیم (برای سادگی MVP)
    first = pending[0]
    other_id = first.country_a_id if first.country_a_id != country.id else first.country_b_id
    other_name = await _country_name(session, other_id)
    await callback.message.edit_text(
        "\n".join(lines) + f"\n\nپاسخ به #{first.id} ({other_name}):",
        reply_markup=pending_treaty_keyboard(first),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("taccept:"))
async def on_treaty_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    treaty_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    try:
        treaty = await diplomacy.respond_to_treaty(
            session, treaty_id=treaty_id, responder_country_id=country.id, accept=True
        )
    except DiplomacyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.edit_text("✅ پیمان فعال شد.", reply_markup=diplomacy_menu_keyboard())
    await callback.answer()

    proposer_telegram_id = await identity.get_telegram_id_for_country(session, treaty.proposed_by_id)
    await notify_user(
        callback.bot, proposer_telegram_id,
        f"✅ {country.display_name} پیشنهاد پیمانت رو قبول کرد!",
    )


@router.callback_query(F.data.startswith("treject:"))
async def on_treaty_reject(callback: CallbackQuery, session: AsyncSession) -> None:
    treaty_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    try:
        await diplomacy.respond_to_treaty(
            session, treaty_id=treaty_id, responder_country_id=country.id, accept=False
        )
    except DiplomacyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.edit_text("❌ پیمان رد شد.", reply_markup=diplomacy_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "dip:active")
async def on_active_treaties(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    active = await diplomacy.list_active_treaties_for(session, country.id)
    if not active:
        await callback.answer("پیمان فعالی نداری.", show_alert=True)
        return

    first = active[0]
    other_id = first.country_a_id if first.country_a_id != country.id else first.country_b_id
    other_name = await _country_name(session, other_id)
    lines = ["📋 پیمان‌های فعال:\n"]
    for t in active:
        oid = t.country_a_id if t.country_a_id != country.id else t.country_b_id
        oname = await _country_name(session, oid)
        lines.append(f"#{t.id} — {TREATY_TYPE_LABELS[t.treaty_type]} با {oname}")

    await callback.message.edit_text(
        "\n".join(lines) + f"\n\nلغو #{first.id} ({other_name})؟",
        reply_markup=active_treaty_keyboard(first),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tcancel:"))
async def on_treaty_cancel(callback: CallbackQuery, session: AsyncSession) -> None:
    treaty_id = int(callback.data.split(":", 1)[1])
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    try:
        await diplomacy.cancel_treaty(session, treaty_id=treaty_id, requester_country_id=country.id)
    except DiplomacyError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await callback.message.edit_text("🚫 پیمان لغو شد.", reply_markup=diplomacy_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "dip:statements")
async def on_statements_list(callback: CallbackQuery, session: AsyncSession) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    statements = await diplomacy.list_recent_statements(session, country.world_id)
    await callback.message.edit_text(
        "📜 بیانیه‌های اخیر:" if statements else "هنوز بیانیه‌ای ثبت نشده.",
        reply_markup=statements_menu_keyboard(statements),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sview:"))
async def on_statement_view(callback: CallbackQuery, session: AsyncSession) -> None:
    from bot.models.diplomacy import Statement

    statement_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(select(Statement).where(Statement.id == statement_id))
    statement = result.scalar_one_or_none()
    if statement is None:
        await callback.answer("این بیانیه دیگه وجود نداره.", show_alert=True)
        return

    author_name = await _country_name(session, statement.author_country_id)
    counts = await diplomacy.statement_counts(session, statement_id)
    text = (
        f"📜 {statement.title}\n"
        f"از طرف: {author_name}\n\n"
        f"{statement.body}\n\n"
        f"✅ حمایت: {counts[StatementReactionType.SUPPORT]} | "
        f"⛔ محکومیت: {counts[StatementReactionType.CONDEMN]}"
    )
    await callback.message.edit_text(text, reply_markup=statement_action_keyboard(statement_id))
    await callback.answer()


@router.callback_query(F.data.startswith("ssupport:") | F.data.startswith("scondemn:"))
async def on_statement_react(callback: CallbackQuery, session: AsyncSession) -> None:
    action, statement_id_raw = callback.data.split(":")
    statement_id = int(statement_id_raw)
    reaction = (
        StatementReactionType.SUPPORT if action == "ssupport" else StatementReactionType.CONDEMN
    )

    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    await diplomacy.react_to_statement(
        session, statement_id=statement_id, country_id=country.id, reaction=reaction
    )
    await callback.answer("ثبت شد.")
    await on_statement_view(callback, session)


@router.callback_query(F.data == "snew")
async def on_statement_new_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    country = await _current_country(session, callback.from_user)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return
    await state.set_state(StatementStates.waiting_title)
    await callback.message.edit_text("عنوان بیانیه رو بفرست:")
    await callback.answer()


@router.message(StatementStates.waiting_title)
async def on_statement_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("عنوان نمی‌تونه خالی باشه. دوباره بفرست.")
        return
    await state.update_data(title=title)
    await state.set_state(StatementStates.waiting_body)
    await message.answer("متن بیانیه رو بفرست:")


@router.message(StatementStates.waiting_body)
async def on_statement_body(message: Message, session: AsyncSession, state: FSMContext) -> None:
    body = (message.text or "").strip()
    if not body:
        await message.answer("متن نمی‌تونه خالی باشه. دوباره بفرست.")
        return

    data = await state.get_data()
    country = await _current_country(session, message.from_user)
    if country is None:
        await state.clear()
        await message.answer("هنوز کشوری نداری.")
        return

    try:
        await diplomacy.post_statement(
            session, world_id=country.world_id, author_country_id=country.id,
            title=data["title"], body=body,
        )
    except DiplomacyError as exc:
        await message.answer(f"❌ {exc}")
        return

    await state.clear()
    await message.answer("✅ بیانیه ثبت شد.", reply_markup=diplomacy_menu_keyboard())
