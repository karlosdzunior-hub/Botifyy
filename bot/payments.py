import hashlib
import logging
from aiogram import Bot
from aiogram.types import LabeledPrice
from config import BOTIFY_LABEL_PREFIX

logger = logging.getLogger(__name__)

CREDIT_PACKAGES = [
    {"credits": 150,  "rub": 149,  "stars": 99,  "label": "💼 Стартовый"},
    {"credits": 300,  "rub": 299,  "stars": 199, "label": "🚀 Базовый"},
    {"credits": 600,  "rub": 549,  "stars": 369, "label": "⚡ Продвинутый"},
    {"credits": 1000, "rub": 890,  "stars": 599, "label": "👑 Максимальный"},
]


def get_package(credits: int) -> dict | None:
    for p in CREDIT_PACKAGES:
        if p["credits"] == credits:
            return p
    return None


async def send_stars_invoice(bot: Bot, chat_id: int, credits: int):
    pkg = get_package(credits)
    if not pkg:
        return False
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"{pkg['label']} — {credits} кредитов",
        description=(
            f"Пополнение баланса Botify на {credits} кредитов.\n"
            f"Кредиты зачисляются мгновенно после оплаты."
        ),
        payload=f"credits:{credits}",
        currency="XTR",
        prices=[LabeledPrice(label=f"{credits} кредитов", amount=pkg["stars"])],
    )
    return True


def build_yoomoney_url(wallet: str, telegram_id: int, credits: int, rub: int, bot_username: str) -> str:
    import urllib.parse
    label = f"{BOTIFY_LABEL_PREFIX}{telegram_id}_{credits}"
    params = {
        "receiver": wallet,
        "quickpay-form": "button",
        "targets": f"Botify: {credits} кредитов",
        "sum": str(rub),
        "label": label,
        "successURL": f"https://t.me/{bot_username}",
    }
    return "https://yoomoney.ru/quickpay/confirm.xml?" + urllib.parse.urlencode(params, encoding="utf-8")


def verify_yoomoney_notification(data: dict, secret: str) -> bool:
    fields = [
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        secret,
        data.get("label", ""),
    ]
    computed = hashlib.sha1("&".join(fields).encode("utf-8")).hexdigest()
    return computed == data.get("sha1_hash", "")


def parse_yoomoney_label(label: str) -> tuple[int, int] | tuple[None, None]:
    try:
        parts = label.split("_")
        return int(parts[0]), int(parts[1])
    except Exception:
        return None, None
