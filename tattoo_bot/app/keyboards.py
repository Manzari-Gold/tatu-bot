from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.config import settings


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Записаться"))
    builder.row(KeyboardButton(text="Портфолио"), KeyboardButton(text="Контакты"))
    if is_admin:
        builder.row(KeyboardButton(text="Админ-панель"))
    return builder.as_markup(resize_keyboard=True)


def subscribe_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Подписаться", url=settings.channel_url),
    )
    builder.row(
        InlineKeyboardButton(text="Проверить подписку", callback_data="check_sub"),
    )
    return builder.as_markup()


def slots_kb(slots: list[tuple[int, date]]) -> InlineKeyboardMarkup:
    from app.utils import format_date_ru

    builder = InlineKeyboardBuilder()
    for slot_id, slot_date in slots:
        builder.row(
            InlineKeyboardButton(
                text=format_date_ru(slot_date),
                callback_data=f"book_slot:{slot_id}",
            )
        )
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="book_cancel"))
    return builder.as_markup()


def cancel_booking_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="book_cancel"))
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Все записи", callback_data="admin:bookings"),
    )
    builder.row(
        InlineKeyboardButton(text="База клиентов", callback_data="admin:clients"),
    )
    builder.row(
        InlineKeyboardButton(text="Управление датами", callback_data="admin:slots"),
    )
    builder.row(
        InlineKeyboardButton(text="Портфолио", callback_data="admin:portfolio"),
    )
    builder.row(InlineKeyboardButton(text="Закрыть", callback_data="admin:close"))
    return builder.as_markup()


def admin_slots_kb(slots: list[tuple[int, date, int]]) -> InlineKeyboardMarkup:
    from app.utils import format_date_ru

    builder = InlineKeyboardBuilder()
    for slot_id, slot_date, count in slots:
        label = f"{format_date_ru(slot_date)} ({count} зап.)"
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin_slot:{slot_id}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="Добавить дату", callback_data="admin:add_slot"),
    )
    builder.row(InlineKeyboardButton(text="Назад", callback_data="admin:back"))
    return builder.as_markup()


def admin_slot_actions_kb(slot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Удалить дату",
            callback_data=f"admin:del_slot:{slot_id}",
        )
    )
    builder.row(InlineKeyboardButton(text="Назад", callback_data="admin:slots"))
    return builder.as_markup()


def admin_portfolio_kb(count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Добавить фото", callback_data="admin:add_photo"),
    )
    if count > 0:
        builder.row(
            InlineKeyboardButton(
                text="Очистить портфолио",
                callback_data="admin:clear_portfolio",
            )
        )
    builder.row(InlineKeyboardButton(text="Назад", callback_data="admin:back"))
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Назад", callback_data="admin:back"))
    return builder.as_markup()
