from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.buildings import BuildingCategory, BuildingType

CATEGORY_LABELS: dict[BuildingCategory, str] = {
    BuildingCategory.RESOURCE: "⛏ منابع",
    BuildingCategory.POWER: "⚡ برق",
    BuildingCategory.FOOD: "🌾 غذا",
    BuildingCategory.WELFARE: "🏥 رفاه",
    BuildingCategory.MILITARY: "🪖 نظامی",
    BuildingCategory.STRATEGIC: "🛰 استراتژیک",
}

BUILDING_LABELS: dict[BuildingType, str] = {
    BuildingType.STEEL_MINE: "معدن فولاد",
    BuildingType.URANIUM_MINE: "معدن اورانیوم",
    BuildingType.OIL_WELL: "چاه نفت",
    BuildingType.REFINERY: "پالایشگاه",
    BuildingType.STEEL_INDUSTRY: "صنایع فولاد",
    BuildingType.WIND_PLANT: "نیروگاه بادی",
    BuildingType.SOLAR_PLANT: "نیروگاه خورشیدی",
    BuildingType.HYDRO_PLANT: "نیروگاه آبی",
    BuildingType.NUCLEAR_PLANT: "نیروگاه هسته‌ای",
    BuildingType.FARM: "کشاورزی",
    BuildingType.RANCH: "دامداری",
    BuildingType.HOSPITAL: "بیمارستان",
    BuildingType.POLICE_STATION: "ایستگاه پلیس",
    BuildingType.UNIVERSITY: "دانشگاه",
    BuildingType.GARRISON: "پادگان",
    BuildingType.AIRPORT: "فرودگاه",
    BuildingType.PORT: "بندر",
    BuildingType.MISSILE_SILO: "سیلوی موشکی",
    BuildingType.TANK_FACTORY: "کارخانه تانک",
    BuildingType.AIRCRAFT_FACTORY: "کارخانه هوایی",
    BuildingType.SHIPYARD: "کارخانه کشتی",
    BuildingType.MISSILE_FACTORY: "کارخانه موشک",
    BuildingType.COMMAND_HQ: "ستاد فرماندهی",
    BuildingType.RADAR: "رادار",
    BuildingType.LAB: "آزمایشگاه",
    BuildingType.SPACE_CENTER: "مرکز فضایی",
}


def category_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"bcat:{cat.value}")]
        for cat, label in CATEGORY_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def buildings_in_category_keyboard(
    buildings: list[BuildingType],
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BUILDING_LABELS[bt], callback_data=f"bview:{bt.value}")]
        for bt in buildings
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:buildings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def building_action_keyboard(building_type: BuildingType) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬆️ ارتقا / ساخت", callback_data=f"bupgrade:{building_type.value}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:buildings")],
        ]
    )
