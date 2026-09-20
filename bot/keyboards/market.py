from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.market import MarketListing
from bot.models.resources import ResourceType

ITEM_LABELS: dict[str, str] = {
    "money": "💰 پول",
    ResourceType.STEEL.value: "🔩 فولاد",
    ResourceType.OIL.value: "🛢 نفت",
    ResourceType.URANIUM.value: "☢️ اورانیوم",
    ResourceType.FOOD.value: "🌾 غذا",
    ResourceType.POWER.value: "⚡ برق",
}


def market_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 آگهی‌های باز", callback_data="mkt:listings")],
            [InlineKeyboardButton(text="➕ ثبت آگهی جدید", callback_data="mkt:new")],
            [InlineKeyboardButton(text="📦 آگهی‌های من", callback_data="mkt:mine")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")],
        ]
    )


def item_choice_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"{callback_prefix}:{code}")]
        for code, label in ITEM_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def listing_item_keyboard(listing: MarketListing) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 خرید", callback_data=f"mbuy:{listing.id}")]]
    )


def my_listing_item_keyboard(listing: MarketListing) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 لغو آگهی", callback_data=f"mcancel:{listing.id}")]
        ]
    )


def back_to_market_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:market")]]
    )
