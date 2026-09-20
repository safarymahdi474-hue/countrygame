from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.military import CATEGORY_LABELS
from bot.models.country import Country
from bot.models.military import UnitCategory


def war_category_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"acat:{cat.value}")]
        for cat, label in CATEGORY_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="🛰 شناسایی کشورها", callback_data="scout:menu")])
    rows.append([InlineKeyboardButton(text="🚢 کاروان آبی‌خاکی", callback_data="amenu:menu")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def target_selection_keyboard(
    category: UnitCategory, countries: list[Country]
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=country.display_name, callback_data=f"atarget:{category.value}:{country.id}"
        )]
        for country in countries
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:war")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_attack_keyboard(category: UnitCategory, target_country_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⚔️ حمله با همه‌ی نیروی این دسته",
                callback_data=f"aconfirm:{category.value}:{target_country_id}",
            )],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"acat:{category.value}")],
        ]
    )


def confirm_amphibious_keyboard(target_country_id: int, transport_qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"🚢 حمله با {transport_qty} ناو ترابری",
                callback_data=f"amconfirm:{target_country_id}:{transport_qty}",
            )],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:war")],
        ]
    )


def scout_target_keyboard(countries: list[Country]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=country.display_name, callback_data=f"ascout:{country.id}")]
        for country in countries
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:war")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def occupy_offer_keyboard(target_country_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏴 اشغالش کن (۳ روز)", callback_data=f"aoccupy:{target_country_id}")],
            [InlineKeyboardButton(text="بی‌خیال", callback_data="menu:war")],
        ]
    )


def amphibious_target_keyboard(countries: list[Country]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=country.display_name, callback_data=f"amtarget:{country.id}")]
        for country in countries
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:war")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
