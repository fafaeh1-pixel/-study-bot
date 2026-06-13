import asyncio
import database.models  # noqa: F401

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from logger import logger
from bot.middlewares.db_middleware import DatabaseMiddleware
from bot.middlewares.user_middleware import UserMiddleware
from bot.handlers import (
    start_handler,
    study_log_handler,
    report_handler,
    reminder_handler,
    ai_handler,
    voice_handler,
)
from bot.handlers import premium_handler
from database.engine import engine
from database.models import Base
from reminders.scheduler import start_scheduler, stop_scheduler


async def on_startup(bot: Bot) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler(bot)
    logger.info("دیتابیس آماده شد")
    me = await bot.get_me()
    logger.info(f"ربات @{me.username} شروع به کار کرد")


async def on_shutdown(bot: Bot) -> None:
    stop_scheduler()
    logger.info("ربات متوقف شد")
    await bot.session.close()


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(UserMiddleware())

    dp.include_router(start_handler.router)
    dp.include_router(study_log_handler.router)
    dp.include_router(report_handler.router)
    dp.include_router(reminder_handler.router)
    dp.include_router(ai_handler.router)
    dp.include_router(voice_handler.router)
    dp.include_router(premium_handler.router)   # ← اضافه شد

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("StudyBot Pro در حال راه‌اندازی...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())