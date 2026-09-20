from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.country import Country
from bot.models.diplomacy import Statement, Treaty, TreatyType

TREATY_TYPE_LABELS: dict[TreatyType, str] = {
    TreatyType.NON_AGGRESSION: "🕊 عدم‌تجاوز",
    TreatyType.ALLIANCE: "🛡 اتحاد",
}


def diplomacy_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🤝 پیشنهاد پیمان", callback_data="dip:propose")],
            [InlineKeyboardButton(text="📥 پیمان‌های در انتظار", callback_data="dip:pending")],
            [InlineKeyboardButton(text="📋 پیمان‌های فعال", callback_data="dip:active")],
            [InlineKeyboardButton(text="📜 بیانیه‌ها", callback_data="dip:statements")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")],
        ]
    )


def treaty_target_keyboard(countries: list[Country]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=c.display_name, callback_data=f"tpropose:{c.id}")]
        for c in countries
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:diplomacy")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def treaty_type_keyboard(target_country_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"ttype:{t.value}:{target_country_id}")]
        for t, label in TREATY_TYPE_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="dip:propose")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pending_treaty_keyboard(treaty: Treaty) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ قبول", callback_data=f"taccept:{treaty.id}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"treject:{treaty.id}"),
            ],
        ]
    )


def active_treaty_keyboard(treaty: Treaty) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 لغو پیمان", callback_data=f"tcancel:{treaty.id}")],
        ]
    )


def statements_menu_keyboard(statements: list[Statement]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📜 {s.title[:40]}", callback_data=f"sview:{s.id}")]
        for s in statements
    ]
    rows.append([InlineKeyboardButton(text="✍️ بیانیه‌ی جدید", callback_data="snew")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:diplomacy")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def statement_action_keyboard(statement_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ حمایت", callback_data=f"ssupport:{statement_id}"),
                InlineKeyboardButton(text="⛔ محکومیت", callback_data=f"scondemn:{statement_id}"),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="dip:statements")],
        ]
    )
