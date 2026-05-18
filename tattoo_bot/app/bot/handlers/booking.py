from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import BookingStates
from app.config import settings
from app.database import async_session
from app.keyboards import cancel_booking_kb, main_menu_kb, slots_kb
from app.services import (
    create_booking,
    get_available_slots,
    get_or_create_user,
    get_slot_by_id,
    slot_is_available,
    user_has_booking_on_slot,
)
from app.texts import (
    BOOKING_ALREADY,
    BOOKING_CHOOSE_DAY,
    BOOKING_ENTER_NAME,
    BOOKING_ENTER_PHONE,
    BOOKING_INVALID_PHONE,
    BOOKING_NO_SLOTS,
    BOOKING_SLOT_TAKEN,
    BOOKING_SUCCESS,
)
from app.utils import format_date_ru, is_valid_phone

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


@router.message(F.text == "Записаться")
async def start_booking(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        slots = await get_available_slots(session)

    if not slots:
        await message.answer(BOOKING_NO_SLOTS)
        return

    await message.answer(
        BOOKING_CHOOSE_DAY,
        reply_markup=slots_kb(slots),
    )


@router.callback_query(F.data == "book_cancel")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("Запись отменена.")
    await callback.message.answer(
        "Главное меню",
        reply_markup=main_menu_kb(_is_admin(callback.from_user.id)),
    )


@router.callback_query(F.data.startswith("book_slot:"))
async def select_slot(callback: CallbackQuery, state: FSMContext) -> None:
    slot_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        slot = await get_slot_by_id(session, slot_id)
        if not slot or not slot.is_active:
            await callback.answer("Дата недоступна", show_alert=True)
            return
        if not await slot_is_available(session, slot_id):
            await callback.answer(BOOKING_SLOT_TAKEN, show_alert=True)
            return
        user = await get_or_create_user(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.full_name,
        )
        if await user_has_booking_on_slot(session, user.id, slot_id):
            await callback.answer(BOOKING_ALREADY, show_alert=True)
            return
        await session.commit()

    await state.update_data(slot_id=slot_id)
    await state.set_state(BookingStates.waiting_name)
    await callback.answer()
    await callback.message.edit_text(BOOKING_ENTER_NAME)
    await callback.message.answer(
        "Введите имя в сообщении ниже:",
        reply_markup=cancel_booking_kb(),
    )


@router.message(BookingStates.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Введите имя ещё раз:")
        return
    await state.update_data(client_name=name)
    await state.set_state(BookingStates.waiting_phone)
    await message.answer(BOOKING_ENTER_PHONE, reply_markup=cancel_booking_kb())


@router.message(BookingStates.waiting_phone, F.text)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not is_valid_phone(phone):
        await message.answer(BOOKING_INVALID_PHONE)
        return

    data = await state.get_data()
    slot_id = data["slot_id"]
    client_name = data["client_name"]

    async with async_session() as session:
        slot = await get_slot_by_id(session, slot_id)
        if not slot or not await slot_is_available(session, slot_id):
            await state.clear()
            await message.answer(BOOKING_SLOT_TAKEN)
            return

        user = await get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
        )
        booking = await create_booking(
            session, user.id, slot_id, client_name, phone
        )
        slot_date = slot.slot_date
        await session.commit()

        admin_text = (
            f"Новая запись!\n"
            f"Дата: {format_date_ru(slot_date)}\n"
            f"Имя: {client_name}\n"
            f"Телефон: {phone}\n"
            f"Telegram: @{message.from_user.username or '—'} "
            f"(id: {message.from_user.id})"
        )

    await state.clear()
    await message.answer(
        BOOKING_SUCCESS.format(
            date=format_date_ru(slot_date),
            name=client_name,
            phone=phone,
        ),
        reply_markup=main_menu_kb(_is_admin(message.from_user.id)),
    )

    for admin_id in settings.admin_id_list:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception:
            pass
