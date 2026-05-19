import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import start, create_bot, my_bots, credits, hosting, referrals, help

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)

    await init_db()
    logger.info("База данных инициализирована")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(create_bot.router)
    dp.include_router(my_bots.router)
    dp.include_router(credits.router)
    dp.include_router(hosting.router)
    dp.include_router(referrals.router)
    dp.include_router(help.router)

    logger.info("Botify запущен!")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
