import logging
import asyncio
from aiohttp import web
from payments import verify_yoomoney_notification, parse_yoomoney_label
from database import get_user_by_telegram_id, add_credits
from config import YOOMONEY_SECRET, WEBHOOK_PORT

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def yoomoney_handler(request: web.Request) -> web.Response:
    try:
        data = dict(await request.post())
        logger.info(f"ЮMoney уведомление: {data}")

        if not verify_yoomoney_notification(data, YOOMONEY_SECRET):
            logger.warning("ЮMoney: неверная подпись!")
            return web.Response(status=400, text="Bad signature")

        label = data.get("label", "")
        telegram_id, credits = parse_yoomoney_label(label)

        if not telegram_id or not credits:
            logger.warning(f"ЮMoney: не удалось разобрать label={label}")
            return web.Response(status=200)

        amount_paid = float(data.get("amount", 0))
        operation_id = data.get("operation_id", "unknown")

        user = await get_user_by_telegram_id(telegram_id)
        if not user:
            logger.warning(f"ЮMoney: пользователь {telegram_id} не найден")
            return web.Response(status=200)

        await add_credits(
            telegram_id,
            credits,
            f"ЮMoney #{operation_id[:8]} ({amount_paid} ₽)",
            t_type="top_up",
        )

        if _bot:
            try:
                await _bot.send_message(
                    telegram_id,
                    f"✅ <b>Оплата получена!</b>\n\n"
                    f"💳 Зачислено: <b>+{credits} кредитов</b>\n"
                    f"💵 Сумма: <b>{amount_paid} ₽</b>\n\n"
                    f"Нажми /start чтобы начать создавать ботов!",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление {telegram_id}: {e}")

        logger.info(f"ЮMoney: зачислено {credits} кредитов пользователю {telegram_id}")
        return web.Response(status=200)

    except Exception as e:
        logger.error(f"ЮMoney webhook error: {e}")
        return web.Response(status=500)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def start_webhook_server():
    if not YOOMONEY_SECRET:
        logger.info("YOOMONEY_SECRET не задан — webhook-сервер не запускается")
        return

    app = web.Application()
    app.router.add_post("/yoomoney/webhook", yoomoney_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logger.info(f"ЮMoney webhook запущен на порту {WEBHOOK_PORT}")
