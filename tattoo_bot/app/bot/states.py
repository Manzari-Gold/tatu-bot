from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()


class AdminStates(StatesGroup):
    waiting_slot_date = State()
    waiting_portfolio_photo = State()
