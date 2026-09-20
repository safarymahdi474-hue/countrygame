"""
دستورات ادمین. دسترسی به این روتر تو main.py محدود به ADMIN_IDS تنظیمات
می‌شه (با filter روی from_user.id) — این فایل خودش فرض نمی‌کنه چه کسی
صداش می‌زنه، فقط منطق دستورات رو پیاده می‌کنه.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country
from bot.services import season, subscription
from bot.services.season import SeasonError
from bot.services.subscription import activate_vip
from bot.services.wallet import adjust_balance

router = Router(name="admin")


@router.message(Command("admin_help"))
async def admin_help(message: Message) -> None:
    await message.answer(
        "دستورات ادمین:\n"
        "/admin_addmoney <country_id> <amount>\n"
        "/admin_grantvip <telegram_id> <days>\n"
        "/admin_endseason <world_id>\n"
        "/admin_createworld <name> [season_days]\n"
    )


@router.message(Command("admin_createworld"))
async def admin_create_world(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args = (command.args or "").split()
    if not args:
        await message.answer("فرمت درست: /admin_createworld <name> [season_days]")
        return
    name = args[0]
    days = 45
    if len(args) > 1:
        try:
            days = int(args[1])
        except ValueError:
            await message.answer("season_days باید عدد صحیح باشه.")
            return

    try:
        world = await season.create_world(session, name=name, season_length_days=days)
    except SeasonError as exc:
        await message.answer(f"❌ {exc}")
        return

    await message.answer(f"✅ دنیای {world.name} ساخته و فعال شد (طول فصل: {days} روز).")


@router.message(Command("admin_addmoney"))
async def admin_add_money(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("فرمت درست: /admin_addmoney <country_id> <amount>")
        return
    try:
        country_id = int(args[0])
        amount = Decimal(args[1])
    except (ValueError, InvalidOperation):
        await message.answer("country_id باید عدد صحیح و amount باید عدد باشه.")
        return

    country = await session.get(Country, country_id)
    if country is None:
        await message.answer("این کشور پیدا نشد.")
        return

    await adjust_balance(session, country_id, None, amount, source="admin:grant")
    await message.answer(f"✅ ${amount:,.0f} به خزانه‌ی {country.display_name} اضافه شد.")


@router.message(Command("admin_grantvip"))
async def admin_grant_vip(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer("فرمت درست: /admin_grantvip <country_id> <days>")
        return
    try:
        country_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await message.answer("هر دو آرگومان باید عدد صحیح باشن.")
        return

    country = await session.get(Country, country_id)
    if country is None:
        await message.answer("این کشور پیدا نشد.")
        return

    await activate_vip(session, country_id, duration_days=days)
    await message.answer(f"✅ VIP برای {country.display_name} به مدت {days} روز فعال شد.")


@router.message(Command("admin_endseason"))
async def admin_end_season(message: Message, command: CommandObject, session: AsyncSession) -> None:
    args = (command.args or "").split()
    if len(args) != 1:
        await message.answer("فرمت درست: /admin_endseason <world_id>")
        return
    try:
        world_id = int(args[0])
    except ValueError:
        await message.answer("world_id باید عدد صحیح باشه.")
        return

    try:
        world = await season.end_world(session, world_id)
    except SeasonError as exc:
        await message.answer(f"❌ {exc}")
        return

    await message.answer(f"✅ دنیای {world.name} بسته شد.")
