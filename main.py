import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from bot.config import settings
from bot.database import db
from bot.handlers import get_all_routers
from bot.utils.scheduler import start_scheduler


async def on_startup(bot: Bot):
    await db.connect()
    start_scheduler(bot)
    me = await bot.get_me()
    logger.success(f"Bot started: @{me.username}")


async def on_shutdown(bot: Bot):
    await db.close()
    logger.info("Bot stopped")


async def main():
    logger.add(
        "data/bot.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO"
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    for router in get_all_routers():
        dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
