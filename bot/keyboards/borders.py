from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.diplomacy import BorderStatus, CountryBorderPolicy

BORDER_LABELS: dict[str, str] = {
    "ground_status": "🪖 زمینی",
    "air_status": "✈️ هوایی",
    "naval_status": "🚢 دریایی",
    "trade_status": "📦 تجاری",
}

STATUS_LABELS: dict[BorderStatus, str] = {
    BorderStatus.CLOSED: "🔴 بسته",
    BorderStatus.LIMITED: "🟡 محدود",
    BorderStatus.OPEN: "🟢 باز",
}

STATUS_CYCLE: dict[BorderStatus, BorderStatus] = {
    BorderStatus.CLOSED: BorderStatus.LIMITED,
    BorderStatus.LIMITED: BorderStatus.OPEN,
    BorderStatus.OPEN: BorderStatus.CLOSED,
}


def borders_menu_keyboard(policy: CountryBorderPolicy) -> InlineKeyboardMarkup:
    rows = []
    for field, label in BORDER_LABELS.items():
        status: BorderStatus = getattr(policy, field)
        rows.append([
            InlineKeyboardButton(
                text=f"{label}: {STATUS_LABELS[status]} (برای تغییر بزن)",
                callback_data=f"border:{field}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
