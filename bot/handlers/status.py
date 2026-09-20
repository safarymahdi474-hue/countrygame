from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import back_to_menu_keyboard
from bot.models.resources import ResourceType
from bot.services import identity, occupation, scoring, season, world_events
from bot.services.power import compute_power_balance
from bot.services.wallet import get_balance

router = Router(name="status")

RESOURCE_LABELS: dict[ResourceType, str] = {
    ResourceType.STEEL: "🔩 فولاد",
    ResourceType.OIL: "🛢 نفت",
    ResourceType.URANIUM: "☢️ اورانیوم",
    ResourceType.FOOD: "🌾 غذا",
}


@router.callback_query(F.data == "menu:status")
async def on_status(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    country = await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    country = await scoring.recompute_scores(session, country.id)

    lines = [
        f"🏛 {country.display_name}",
        f"💰 خزانه: ${country.treasury:,.0f}" + (" ⚠️ بدهکار!" if country.treasury < 0 else ""),
    ]
    if await occupation.is_occupied(session, country.id):
        lines.append(f"🏴 اشغال‌شده — تولید نصف شده، تا {country.occupied_until:%Y-%m-%d %H:%M}")
    occupied_count = await occupation.count_occupied_by(session, country.id)
    if occupied_count:
        lines.append(f"🏴 {occupied_count} کشور تحت اشغال تو")

    active_event = await world_events.get_active_event(session, world.id)
    if active_event is not None:
        effect = world_events.EVENT_EFFECTS[active_event.event_type]
        lines.append(f"🌐 رویداد دنیا: {effect.description}")

    lines += ["", "📦 منابع:"]
    for res_type, label in RESOURCE_LABELS.items():
        amount = await get_balance(session, country.id, res_type)
        lines.append(f"  {label}: {amount:,.0f}")

    produced, consumed = await compute_power_balance(session, country.id)
    lines.append(f"  ⚡ برق: {consumed:,.0f}/{produced:,.0f} مصرف/تولید")

    lines += [
        "",
        "📊 امتیازها:",
        f"  اقتصادی: {country.score_economic:,.0f}",
        f"  نظامی: {country.score_military:,.0f}",
        f"  قلمرو: {country.score_territory:,.0f}",
        f"  توسعه: {country.score_development:,.0f}",
        f"  دیپلماسی: {country.score_diplomacy:,.0f}",
    ]

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:ledger")
async def on_ledger(callback: CallbackQuery, session: AsyncSession) -> None:
    import datetime as dt

    from bot.services import ledger

    user = await identity.get_or_create_user(
        session, telegram_id=callback.from_user.id, username=callback.from_user.username
    )
    world = await identity.get_active_world_for_user(session, user)
    country = await identity.get_country_for_user(session, user_id=user.id, world_id=world.id)
    if country is None:
        await callback.answer("هنوز کشوری نداری.", show_alert=True)
        return

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
    summary = await ledger.summary_since(session, country.id, since=since)

    labels = {"money": "💰 پول", "steel": "🔩 فولاد", "oil": "🛢 نفت", "uranium": "☢️ اورانیوم", "food": "🌾 غذا"}
    lines = [f"📒 دفتر کل {country.display_name} (۷ روز اخیر):\n"]
    if not summary:
        lines.append("هنوز تراکنشی ثبت نشده.")
    else:
        for item, totals in summary.items():
            label = labels.get(item.value, item.value)
            lines.append(
                f"{label}: درآمد {totals['income']:,.0f} | هزینه {totals['expense']:,.0f} | خالص {totals['net']:+,.0f}"
            )

    await callback.message.edit_text("\n".join(lines), reply_markup=back_to_menu_keyboard())
    await callback.answer()
