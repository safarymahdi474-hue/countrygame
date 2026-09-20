from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.country import CountryTier
from bot.services.economy import STARTING_TREASURY

# فهرست کشورهای قابل‌انتخاب
NATION_CHOICES: list[tuple[str, str, str]] = [
    ("IT", "🇮🇹", "ایتالیا"),
    ("FR", "🇫🇷", "فرانسه"),
    ("DE", "🇩🇪", "آلمان"),
    ("TR", "🇹🇷", "ترکیه"),
    ("BR", "🇧🇷", "برزیل"),
    ("EG", "🇪🇬", "مصر"),
    ("IN", "🇮🇳", "هند"),
    ("JP", "🇯🇵", "ژاپن"),
    ("GB", "🇬🇧", "بریتانیا"),
    ("ES", "🇪🇸", "اسپانیا"),
    ("RU", "🇷🇺", "روسیه"),
    ("CN", "🇨🇳", "چین"),
    ("US", "🇺🇸", "آمریکا"),
    ("CA", "🇨🇦", "کانادا"),
    ("MX", "🇲🇽", "مکزیک"),
    ("AR", "🇦🇷", "آرژانتین"),
    ("ZA", "🇿🇦", "آفریقای جنوبی"),
    ("NG", "🇳🇬", "نیجریه"),
    ("SA", "🇸🇦", "عربستان"),
    ("AE", "🇦🇪", "امارات"),
    ("KR", "🇰🇷", "کره‌ی جنوبی"),
    ("SE", "🇸🇪", "سوئد"),
    ("PL", "🇵🇱", "لهستان"),
    ("UA", "🇺🇦", "اوکراین"),
    ("GR", "🇬🇷", "یونان"),
    ("NL", "🇳🇱", "هلند"),
    ("AU", "🇦🇺", "استرالیا"),
    ("ID", "🇮🇩", "اندونزی"),
    ("PK", "🇵🇰", "پاکستان"),
    ("VN", "🇻🇳", "ویتنام"),
]

TIER_LABELS: dict[CountryTier, str] = {
    CountryTier.STANDARD: "🔹 استاندارد",
    CountryTier.ADVANCED: "🔸 پیشرفته",
    CountryTier.ELITE: "💎 نخبه",
}


NATIONS_PER_PAGE = 8


def nation_selection_keyboard(world_id: int, page: int = 0) -> InlineKeyboardMarkup:
    total_pages = (len(NATION_CHOICES) - 1) // NATIONS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    start = page * NATIONS_PER_PAGE
    chunk = NATION_CHOICES[start:start + NATIONS_PER_PAGE]

    rows = [
        [InlineKeyboardButton(text=f"{flag} {name}", callback_data=f"pick_nation:{world_id}:{code}")]
        for code, flag, name in chunk
    ]

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ قبلی", callback_data=f"nations_page:{world_id}:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="بعدی ▶️", callback_data=f"nations_page:{world_id}:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def tier_selection_keyboard(world_id: int, nation_code: str) -> InlineKeyboardMarkup:
    rows = []
    for tier, label in TIER_LABELS.items():
        treasury = STARTING_TREASURY[tier]
        rows.append([
            InlineKeyboardButton(
                text=f"{label} — خزانه‌ی اولیه ${treasury:,.0f}",
                callback_data=f"pick_tier:{world_id}:{nation_code}:{tier.value}",
            )
        ])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"menu:pick_nation_back:{world_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def world_selection_keyboard(worlds: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🌐 {w.name}", callback_data=f"pick_world:{w.id}")]
        for w in worlds
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def switch_country_keyboard(countries: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🏛 {c.display_name}", callback_data=f"switch_country:{c.id}")]
        for c in countries
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📊 وضعیت کشور", callback_data="menu:status")],
        [InlineKeyboardButton(text="📒 دفتر کل", callback_data="menu:ledger")],
        [InlineKeyboardButton(text="🏗 زیرساخت", callback_data="menu:buildings")],
        [InlineKeyboardButton(text="🪖 ارتش", callback_data="menu:military")],
        [InlineKeyboardButton(text="⚔️ جنگ", callback_data="menu:war")],
        [InlineKeyboardButton(text="🤝 دیپلماسی", callback_data="menu:diplomacy")],
        [InlineKeyboardButton(text="🛒 بازار جهانی", callback_data="menu:market")],
        [InlineKeyboardButton(text="🚧 مرزها", callback_data="menu:borders")],
        [InlineKeyboardButton(text="🌍 رتبه‌بندی", callback_data="menu:ranking")],
        [InlineKeyboardButton(text="🏆 دستاوردها", callback_data="menu:achievements")],
        [InlineKeyboardButton(text="🔄 تعویض کشور", callback_data="menu:switch_country")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:main")]]
    )
