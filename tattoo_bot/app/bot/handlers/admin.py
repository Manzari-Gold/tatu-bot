from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import AdminStates
from app.config import settings
from app.database import async_session
from app.keyboards import (
    admin_back_kb,
    admin_menu_kb,
    admin_portfolio_kb,
    admin_slot_actions_kb,
    admin_slots_kb,
    main_menu_kb,
)
from app.services import (
    add_portfolio_photo,
    add_slot,
    clear_portfolio,
    delete_slot,
    get_all_bookings,
    get_bookings_by_date,
    get_clients_summary,
    get_portfolio,
    get_slots_with_counts,
)
from app.texts import ADMIN_MENU, ADMIN_NOT_ALLOWED
from app.utils import format_date_ru

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


async def show_admin_menu(message: Message) -> None:
    await message.answer(ADMIN_MENU, reply_markup=admin_menu_kb())


@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(ADMIN_NOT_ALLOWED)
        return
    await show_admin_menu(message)


@router.callback_query(F.data == "admin:close")
async def admin_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.delete()


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(ADMIN_MENU, reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:bookings")
async def admin_bookings(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        grouped = await get_bookings_by_date(session)

    if not grouped:
        text = "Записей пока нет."
    else:
        lines = ["<b>Все записи по дням:</b>\n"]
        for slot_date, bookings in grouped.items():
            lines.append(f"\n<b>{format_date_ru(slot_date)}</b>")
            for b in bookings:
                tg = f"@{b.user.username}" if b.user.username else f"id{b.user.telegram_id}"
                lines.append(
                    f"  • {b.client_name} — {b.phone} ({tg})"
                )
        text = "\n".join(lines)

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=admin_back_kb())


@router.callback_query(F.data == "admin:clients")
async def admin_clients(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        bookings = await get_clients_summary(session)

    if not bookings:
        text = "База клиентов пуста."
    else:
        lines = ["<b>База клиентов:</b>\n"]
        for i, b in enumerate(bookings, 1):
            tg = f"@{b.user.username}" if b.user.username else f"id{b.user.telegram_id}"
            lines.append(
                f"{i}. <b>{b.client_name}</b>\n"
                f"   Тел: {b.phone}\n"
                f"   Дата: {format_date_ru(b.slot.slot_date)}\n"
                f"   TG: {tg}\n"
            )
        text = "\n".join(lines)

    await callback.answer()
    await callback.message.edit_text(text, reply_markup=admin_back_kb())


@router.callback_query(F.data == "admin:slots")
async def admin_slots(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        slots = await get_slots_with_counts(session)

    text = "Управление датами записи:"
    await callback.answer()
    await callback.message.edit_text(
        text,
        reply_markup=admin_slots_kb(slots),
    )


@router.callback_query(F.data.startswith("admin_slot:"))
async def admin_slot_detail(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    slot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        from app.services import get_slot_by_id

        slot = await get_slot_by_id(session, slot_id)
        if not slot:
            await callback.answer("Дата не найдена", show_alert=True)
            return
        bookings = await get_all_bookings(session)
        day_bookings = [b for b in bookings if b.slot_id == slot_id]

    lines = [f"<b>{format_date_ru(slot.slot_date)}</b>\n"]
    if day_bookings:
        for b in day_bookings:
            lines.append(f"• {b.client_name} — {b.phone}")
    else:
        lines.append("Записей на эту дату нет (слот свободен).")

    await callback.answer()
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_slot_actions_kb(slot_id),
    )


@router.callback_query(F.data.startswith("admin:del_slot:"))
async def admin_delete_slot(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    slot_id = int(callback.data.split(":")[-1])
    async with async_session() as session:
        ok = await delete_slot(session, slot_id)
        await session.commit()
        slots = await get_slots_with_counts(session)

    await callback.answer("Дата удалена" if ok else "Ошибка", show_alert=True)
    await callback.message.edit_text(
        "Управление датами записи:",
        reply_markup=admin_slots_kb(slots),
    )


@router.callback_query(F.data == "admin:add_slot")
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_slot_date)
    await callback.answer()
    await callback.message.edit_text(
        "Введите дату в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>25.05.2026</code>",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminStates.waiting_slot_date, F.text)
async def admin_add_slot_finish(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        slot_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ")
        return

    async with async_session() as session:
        slot = await add_slot(session, slot_date)
        await session.commit()

    await state.clear()
    if slot:
        await message.answer(
            f"Дата добавлена: {format_date_ru(slot_date)}",
            reply_markup=main_menu_kb(True),
        )
    else:
        await message.answer(
            "Такая дата уже есть в расписании.",
            reply_markup=main_menu_kb(True),
        )


@router.callback_query(F.data == "admin:portfolio")
async def admin_portfolio(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    async with async_session() as session:
        photos = await get_portfolio(session)

    await callback.answer()
    await callback.message.edit_text(
        f"Портфолио: {len(photos)} фото",
        reply_markup=admin_portfolio_kb(len(photos)),
    )


@router.callback_query(F.data == "admin:add_photo")
async def admin_add_photo_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_portfolio_photo)
    await callback.answer()
    await callback.message.edit_text(
        "Отправьте фото для портфолио (можно с подписью).",
        reply_markup=admin_back_kb(),
    )


@router.message(AdminStates.waiting_portfolio_photo, F.photo)
async def admin_add_photo_finish(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    file_id = message.photo[-1].file_id
    caption = message.caption

    async with async_session() as session:
        await add_portfolio_photo(session, file_id, caption)
        await session.commit()

    await state.clear()
    await message.answer(
        "Фото добавлено в портфолио.",
        reply_markup=main_menu_kb(True),
    )


@router.callback_query(F.data == "admin:clear_portfolio")
async def admin_clear_portfolio(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    async with async_session() as session:
        await clear_portfolio(session)
        await session.commit()

    await callback.answer("Портфолио очищено", show_alert=True)
    await callback.message.edit_text(
        "Портфолио: 0 фото",
        reply_markup=admin_portfolio_kb(0),
    )
