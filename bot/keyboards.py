from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from payments import CREDIT_PACKAGES


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🤖 Создать бота", callback_data="create_bot"),
        InlineKeyboardButton(text="📱 Создать Mini App", callback_data="create_miniapp"),
    )
    builder.row(
        InlineKeyboardButton(text="📦 Мои боты", callback_data="my_bots"),
        InlineKeyboardButton(text="🖥️ Хостинг", callback_data="hosting"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Кредиты", callback_data="credits"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
    )
    builder.row(InlineKeyboardButton(text="❓ Помощь", callback_data="help"))
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def cancel_dialogue_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_dialogue"))
    return builder.as_markup()


def confirm_creation_keyboard(cost: int, bot_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Генерировать ({cost} кредитов)",
            callback_data=f"confirm_create:{bot_type}",
        ),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_dialogue"),
    )
    return builder.as_markup()


def credits_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Пополнить", callback_data="buy_credits"))
    builder.row(InlineKeyboardButton(text="📋 История", callback_data="credit_history"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def buy_credits_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for pkg in CREDIT_PACKAGES:
        builder.row(InlineKeyboardButton(
            text=f"{pkg['label']} — {pkg['credits']} кр. | ⭐{pkg['stars']} / {pkg['rub']}₽",
            callback_data=f"buy:{pkg['credits']}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="credits"))
    return builder.as_markup()


def payment_method_keyboard(credits: int, stars: int, rub: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"⭐ Telegram Stars — {stars} Stars",
        callback_data=f"pay_stars:{credits}",
    ))
    builder.row(InlineKeyboardButton(
        text=f"💵 ЮMoney — {rub} ₽",
        callback_data=f"pay_yoomoney:{credits}",
    ))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="buy_credits"))
    return builder.as_markup()


def my_bots_keyboard(bots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for bot in bots:
        icon = {"created": "✅", "running": "🟡", "hosted": "🟢", "stopped": "🔴", "error": "⚠️"}.get(bot["status"], "⚪")
        builder.row(InlineKeyboardButton(
            text=f"{icon} {bot['name']}",
            callback_data=f"bot_detail:{bot['id']}",
        ))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def bot_detail_keyboard(bot_id: int, status: str = "created", has_code: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if status == "created" or status == "stopped":
        builder.row(InlineKeyboardButton(text="▶️ Запустить", callback_data=f"run_process:{bot_id}"))
        builder.row(InlineKeyboardButton(text="🖥️ Захостить 24/7", callback_data=f"host_bot:{bot_id}"))

    elif status == "running":
        builder.row(InlineKeyboardButton(text="⏸️ Остановить", callback_data=f"stop_process:{bot_id}"))
        builder.row(InlineKeyboardButton(text="📋 Логи", callback_data=f"logs_process:{bot_id}"))
        builder.row(InlineKeyboardButton(text="🖥️ Захостить 24/7", callback_data=f"host_bot:{bot_id}"))

    elif status == "hosted":
        builder.row(
            InlineKeyboardButton(text="⏸️ Стоп", callback_data=f"stop_bot:{bot_id}"),
            InlineKeyboardButton(text="▶️ Старт", callback_data=f"start_bot:{bot_id}"),
            InlineKeyboardButton(text="🔄 Рестарт", callback_data=f"restart_bot:{bot_id}"),
        )
        builder.row(InlineKeyboardButton(text="📋 Логи", callback_data=f"logs_bot:{bot_id}"))

    if has_code:
        builder.row(InlineKeyboardButton(text="📥 Скачать код", callback_data=f"download_code:{bot_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Мои боты", callback_data="my_bots"))
    return builder.as_markup()


def hosting_plans_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🟢 Мини — 399 ₽/мес", callback_data=f"buy_hosting:{bot_id}:mini"))
    builder.row(InlineKeyboardButton(text="🔵 Стандарт — 890 ₽/мес", callback_data=f"buy_hosting:{bot_id}:standard"))
    builder.row(InlineKeyboardButton(text="🟣 Макс — 1990 ₽/мес", callback_data=f"buy_hosting:{bot_id}:max"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"bot_detail:{bot_id}"))
    return builder.as_markup()


def referrals_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/botify_support"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()
