from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.subscription import is_subscribed
from app.config import settings
from app.database import async_session
from app.keyboards import main_menu_kb, subscribe_kb
from app.services import get_or_create_user, get_portfolio
from app.texts import CHANNEL_SUBSCRIBE, CONTACTS, MAIN_MENU, PORTFOLIO_EMPTY

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with async_session() as session:
        await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
        await session.commit()

    subscribed = await is_subscribed(message.bot, message.from_user.id)
    if not subscribed and not _is_admin(message.from_user.id):
        await message.answer(
            CHANNEL_SUBSCRIBE.format(channel_url=settings.channel_url),
            reply_markup=subscribe_kb(),
        )
        return

    await message.answer(
        MAIN_MENU,
        reply_markup=main_menu_kb(_is_admin(message.from_user.id)),
    )


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery) -> None:
    if await is_subscribed(callback.bot, callback.from_user.id):
        await callback.answer("Подписка подтверждена!", show_alert=True)
        await callback.message.answer(
            MAIN_MENU,
            reply_markup=main_menu_kb(_is_admin(callback.from_user.id)),
        )
    else:
        await callback.answer("Подписка не найдена", show_alert=True)


@router.message(F.text == "Контакты")
async def show_contacts(message: Message) -> None:
    await message.answer(
        CONTACTS.format(
            phone=settings.master_phone,
            telegram=settings.master_telegram,
        )
    )


@router.message(F.text == "Портфолио")
async def show_portfolio(message: Message) -> None:
    async with async_session() as session:
        photos = await get_portfolio(session)

    if not photos:
        await message.answer(PORTFOLIO_EMPTY)
        return

    for photo in photos:
        await message.answer_photo(photo.file_id, caption=photo.caption)


@router.message(Command("admin"))
async def admin_command(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    from app.bot.handlers.admin import show_admin_menu

    await show_admin_menu(message)
