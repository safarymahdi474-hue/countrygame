from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.military import UNIT_CATEGORY, UnitCategory, UnitType

CATEGORY_LABELS: dict[UnitCategory, str] = {
    UnitCategory.GROUND: "🪖 زمینی",
    UnitCategory.AIR: "✈️ هوایی",
    UnitCategory.NAVAL: "🚢 دریایی",
    UnitCategory.MISSILE: "🚀 موشکی",
}

UNIT_LABELS: dict[UnitType, str] = {
    UnitType.INFANTRY: "پیاده‌نظام",
    UnitType.TANK: "تانک",
    UnitType.ARTILLERY: "توپخانه",
    UnitType.FIGHTER: "جنگنده",
    UnitType.BOMBER: "بمب‌افکن",
    UnitType.TRANSPORT_PLANE: "هواپیمای ترابری",
    UnitType.DESTROYER: "ناوشکن",
    UnitType.SUBMARINE: "زیردریایی",
    UnitType.CARRIER: "ناو هواپیمابر",
    UnitType.TRANSPORT_SHIP: "کشتی ترابری",
    UnitType.SHORT_RANGE_MISSILE: "موشک برد کوتاه",
    UnitType.LONG_RANGE_MISSILE: "موشک برد بلند",
    UnitType.AIR_DEFENSE: "پدافند هوایی",
}


def military_category_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"mcat:{cat.value}")]
        for cat, label in CATEGORY_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def units_in_category_keyboard(category: UnitCategory) -> InlineKeyboardMarkup:
    unit_types = [ut for ut, cat in UNIT_CATEGORY.items() if cat == category]
    rows = [
        [InlineKeyboardButton(text=UNIT_LABELS[ut], callback_data=f"munit:{ut.value}")]
        for ut in unit_types
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:military")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def unit_action_keyboard(unit_type: UnitType) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏗 ساخت", callback_data=f"mbuild:{unit_type.value}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:military")],
        ]
    )


def cancel_quantity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ لغو", callback_data="mbuild_cancel")]]
    )
