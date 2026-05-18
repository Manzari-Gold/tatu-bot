from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.bot.subscription import is_subscribed
from app.config import settings
from app.keyboards import subscribe_kb
from app.texts import CHANNEL_SUBSCRIBE


class SubscriptionMiddleware(BaseMiddleware):
    """Проверка подписки на канал для пользовательских действий."""

    ALLOWED_CALLBACKS = frozenset({"check_sub"})
    ALLOWED_TEXTS = frozenset({"/start"})

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        bot: Bot = data["bot"]
        user_id: int | None = None
        skip = False

        if isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            if event.data in self.ALLOWED_CALLBACKS:
                skip = True
            if event.data and event.data.startswith("admin:"):
                if user_id in settings.admin_id_list:
                    return await handler(event, data)
                await event.answer("Нет доступа", show_alert=True)
                return None
            if event.data and (
                event.data.startswith("admin_slot:")
                or event.data.startswith("admin:del_slot:")
            ):
                if user_id in settings.admin_id_list:
                    return await handler(event, data)
                return None

        elif isinstance(event, Message):
            user_id = event.from_user.id
            if event.text in self.ALLOWED_TEXTS:
                skip = True
            if event.text == "Админ-панель" and user_id in settings.admin_id_list:
                return await handler(event, data)

        if user_id is None or skip:
            return await handler(event, data)

        if user_id in settings.admin_id_list:
            return await handler(event, data)

        if not await is_subscribed(bot, user_id):
            text = CHANNEL_SUBSCRIBE.format(channel_url=settings.channel_url)
            if isinstance(event, Message):
                await event.answer(text, reply_markup=subscribe_kb())
            elif isinstance(event, CallbackQuery):
                await event.message.answer(text, reply_markup=subscribe_kb())
                await event.answer()
            return None

        return await handler(event, data)
