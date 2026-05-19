from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
    )
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
        InlineKeyboardButton(text=f"✅ Генерировать ({cost} кредитов)", callback_data=f"confirm_create:{bot_type}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_dialogue"),
    )
    return builder.as_markup()


def credits_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Пополнить", callback_data="buy_credits"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 История", callback_data="credit_history"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    )
    return builder.as_markup()


def buy_credits_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 150 кредитов — 224 ₽", callback_data="buy:150"),
        InlineKeyboardButton(text="💳 300 кредитов — 449 ₽", callback_data="buy:300"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 600 кредитов — 898 ₽", callback_data="buy:600"),
        InlineKeyboardButton(text="💳 1000 кредитов — 1490 ₽", callback_data="buy:1000"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="credits"))
    return builder.as_markup()


def my_bots_keyboard(bots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for bot in bots:
        status_icon = {"created": "✅", "hosted": "🟢", "stopped": "🔴"}.get(bot["status"], "⚪")
        builder.row(
            InlineKeyboardButton(
                text=f"{status_icon} {bot['name']}",
                callback_data=f"bot_detail:{bot['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def bot_detail_keyboard(bot_id: int, is_hosted: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_hosted:
        builder.row(
            InlineKeyboardButton(text="🖥️ Захостить", callback_data=f"host_bot:{bot_id}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="⏸️ Остановить", callback_data=f"stop_bot:{bot_id}"),
            InlineKeyboardButton(text="▶️ Запустить", callback_data=f"start_bot:{bot_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Перезапустить", callback_data=f"restart_bot:{bot_id}"),
        )
    builder.row(InlineKeyboardButton(text="◀️ Мои боты", callback_data="my_bots"))
    return builder.as_markup()


def hosting_plans_keyboard(bot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🟢 Мини — 399 ₽/мес", callback_data=f"buy_hosting:{bot_id}:mini"),
    )
    builder.row(
        InlineKeyboardButton(text="🔵 Стандарт — 890 ₽/мес", callback_data=f"buy_hosting:{bot_id}:standard"),
    )
    builder.row(
        InlineKeyboardButton(text="🟣 Макс — 1990 ₽/мес", callback_data=f"buy_hosting:{bot_id}:max"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"bot_detail:{bot_id}"))
    return builder.as_markup()


def referrals_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/botify_support"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()
