import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 30


async def monitor_bots(bot):
    from database import get_all_hosted_bots, update_bot_status, get_user_telegram_id
    from docker_manager import get_container_status, restart_bot_container

    logger.info("Мониторинг ботов запущен")
    while True:
        try:
            hosted_bots = await get_all_hosted_bots()
            for record in hosted_bots:
                bot_id = record["bot_id"]
                user_tg_id = record["telegram_id"]
                bot_name = record["name"]

                status = await get_container_status(bot_id)

                if status in ("exited", "dead"):
                    logger.warning(f"Бот {bot_id} ({bot_name}) упал, перезапускаем...")
                    restarted = await restart_bot_container(bot_id)
                    if restarted:
                        await update_bot_status(bot_id, "hosted")
                        try:
                            await bot.send_message(
                                user_tg_id,
                                f"⚠️ <b>Бот «{bot_name}» упал и был автоматически перезапущен.</b>\n\n"
                                f"🔄 Статус: работает",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                    else:
                        await update_bot_status(bot_id, "error")
                        try:
                            await bot.send_message(
                                user_tg_id,
                                f"❌ <b>Бот «{bot_name}» упал и не смог перезапуститься.</b>\n\n"
                                f"Обратись в поддержку: @botify_support",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass

        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


async def notify_expiring_hosting(bot):
    from database import get_expiring_hosting

    logger.info("Планировщик уведомлений о хостинге запущен")
    while True:
        try:
            expiring_3d = await get_expiring_hosting(days=3)
            for record in expiring_3d:
                try:
                    await bot.send_message(
                        record["telegram_id"],
                        f"⏰ <b>Хостинг бота «{record['name']}» истекает через 3 дня!</b>\n\n"
                        f"📅 Дата окончания: {record['expires_at'][:10]}\n\n"
                        f"Продли хостинг в разделе 🖥️ Хостинг, чтобы бот продолжал работать.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            expiring_1d = await get_expiring_hosting(days=1)
            for record in expiring_1d:
                try:
                    await bot.send_message(
                        record["telegram_id"],
                        f"🚨 <b>ПОСЛЕДНИЙ ДЕНЬ! Хостинг бота «{record['name']}» истекает завтра!</b>\n\n"
                        f"Без продления бот будет остановлен. Продли прямо сейчас в разделе 🖥️ Хостинг.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Ошибка планировщика хостинга: {e}")

        await asyncio.sleep(3600)
