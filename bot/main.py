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
from scheduler import monitor_bots, notify_expiring_hosting
from webhook_server import start_webhook_server, set_bot

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

    set_bot(bot)

    asyncio.create_task(monitor_bots(bot))
    asyncio.create_task(notify_expiring_hosting(bot))
    asyncio.create_task(start_webhook_server())

    logger.info("Botify запущен! Мониторинг и webhook активны.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
