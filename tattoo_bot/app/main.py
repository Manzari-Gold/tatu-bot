import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.bot import create_bot, create_dispatcher
from app.bot.handlers import setup_routers
from app.config import settings
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = create_bot()
dp = create_dispatcher()
dp.include_router(setup_routers())

_polling_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    await init_db()
    logger.info("Database initialized")

    if settings.use_webhook:
        webhook_url = f"{settings.webhook_host.rstrip('/')}{settings.webhook_path}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.webhook_secret or None,
        )
        logger.info("Webhook set: %s", webhook_url)
    else:
        global _polling_task
        _polling_task = asyncio.create_task(
            dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        )
        logger.info("Bot polling started")

    yield

    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    if settings.use_webhook:
        await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(title="Tattoo Master Bot", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(settings.webhook_path)
async def webhook_handler(request: Request) -> JSONResponse:
    if settings.webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if token != settings.webhook_secret:
            return JSONResponse({"ok": False}, status_code=403)

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()
