import logging
import aiohttp
from aiohttp import web
from payments import verify_yoomoney_notification, parse_yoomoney_label
from database import get_user_by_telegram_id, add_credits
from config import YOOMONEY_SECRET, YOOMONEY_FORWARD_URL, WEBHOOK_PORT, BOTIFY_LABEL_PREFIX

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def yoomoney_handler(request: web.Request) -> web.Response:
    try:
        data = dict(await request.post())
        logger.info(f"ЮMoney уведомление получено: label={data.get('label', '')}")

        if not verify_yoomoney_notification(data, YOOMONEY_SECRET):
            logger.warning("ЮMoney: неверная подпись — отклонено")
            return web.Response(status=400, text="Bad signature")

        label = data.get("label", "")

        if label.startswith(BOTIFY_LABEL_PREFIX):
            await handle_botify_payment(data, label)
        elif YOOMONEY_FORWARD_URL:
            await forward_to_other_service(data)
        else:
            logger.info(f"ЮMoney: label={label!r} не для Botify, игнорируем")

        return web.Response(status=200)

    except Exception as e:
        logger.error(f"ЮMoney webhook error: {e}")
        return web.Response(status=500)


async def handle_botify_payment(data: dict, label: str):
    clean_label = label[len(BOTIFY_LABEL_PREFIX):]
    telegram_id, credits = parse_yoomoney_label(clean_label)

    if not telegram_id or not credits:
        logger.warning(f"ЮMoney Botify: не удалось разобрать label={label!r}")
        return

    amount_paid = float(data.get("amount", 0))
    operation_id = data.get("operation_id", "unknown")

    user = await get_user_by_telegram_id(telegram_id)
    if not user:
        logger.warning(f"ЮMoney Botify: пользователь {telegram_id} не найден")
        return

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
                f"Нажми /start чтобы начать! 🤖",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление {telegram_id}: {e}")

    logger.info(f"ЮMoney Botify: зачислено {credits} кредитов → {telegram_id}")


async def forward_to_other_service(data: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                YOOMONEY_FORWARD_URL,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                logger.info(f"ЮMoney: переслано на {YOOMONEY_FORWARD_URL}, статус={resp.status}")
    except Exception as e:
        logger.error(f"ЮMoney: ошибка пересылки на {YOOMONEY_FORWARD_URL}: {e}")


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def start_webhook_server():
    if not YOOMONEY_SECRET:
        logger.info("YOOMONEY_SECRET не задан — ЮMoney webhook не запускается (Stars работает без него)")
        return

    app = web.Application()
    app.router.add_post("/yoomoney/webhook", yoomoney_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()
    logger.info(f"ЮMoney роутер запущен на порту {WEBHOOK_PORT} (prefix={BOTIFY_LABEL_PREFIX!r})")
