from aiogram import Router

from app.bot.handlers import admin, booking, user


def setup_routers() -> Router:
    root = Router()
    root.include_router(user.router)
    root.include_router(booking.router)
    root.include_router(admin.router)
    return root
