from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_user_bots, get_bot, get_user
from keyboards import my_bots_keyboard, bot_detail_keyboard, hosting_plans_keyboard, back_to_menu_keyboard

router = Router()

STATUS_LABELS = {
    "created": "✅ Создан (не захощен)",
    "hosted": "🟢 Запущен",
    "stopped": "🔴 Остановлен",
}

TYPE_LABELS = {
    "simple": "Простой",
    "medium": "Средний",
    "complex": "Сложный",
    "miniapp_simple": "Mini App (простой)",
    "miniapp_complex": "Mini App (сложный)",
}


@router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery):
    bots = await get_user_bots(callback.from_user.id)

    if not bots:
        await callback.message.edit_text(
            "📦 <b>Мои боты</b>\n\n"
            "У тебя пока нет созданных ботов.\n\n"
            "Нажми 🤖 <b>Создать бота</b>, чтобы начать!",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    text = f"📦 <b>Мои боты</b> — {len(bots)} шт.\n\nВыбери бота для управления:"
    await callback.message.edit_text(
        text,
        reply_markup=my_bots_keyboard(bots),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_detail:"))
async def show_bot_detail(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    status = STATUS_LABELS.get(bot["status"], bot["status"])
    bot_type = TYPE_LABELS.get(bot["bot_type"], bot["bot_type"])
    created_at = bot["created_at"][:10] if bot["created_at"] else "—"

    text = (
        f"🤖 <b>{bot['name']}</b>\n\n"
        f"📋 Тип: {bot_type}\n"
        f"🔹 Статус: {status}\n"
        f"📅 Создан: {created_at}\n\n"
    )

    if bot.get("dialogue_summary"):
        summary_preview = bot["dialogue_summary"][:300]
        if len(bot["dialogue_summary"]) > 300:
            summary_preview += "..."
        text += f"📝 <b>Описание:</b>\n<i>{summary_preview}</i>"

    is_hosted = bot["status"] == "hosted"
    await callback.message.edit_text(
        text,
        reply_markup=bot_detail_keyboard(bot_id, is_hosted),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("host_bot:"))
async def show_hosting_plans(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    await callback.message.edit_text(
        f"🖥️ <b>Хостинг для «{bot['name']}»</b>\n\n"
        f"Выбери тариф:\n\n"
        f"🟢 <b>Мини</b> — 399 ₽/мес\n"
        f"   1 бот • до 2 000 пользователей • автоперезапуск\n\n"
        f"🔵 <b>Стандарт</b> — 890 ₽/мес\n"
        f"   3 бота • до 20 000 пользователей • автоперезапуск + статистика\n\n"
        f"🟣 <b>Макс</b> — 1 990 ₽/мес\n"
        f"   10 ботов • безлимит • приоритетная поддержка",
        reply_markup=hosting_plans_keyboard(bot_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_hosting:"))
async def buy_hosting(callback: CallbackQuery):
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    plan = parts[2]

    plan_names = {"mini": "Мини", "standard": "Стандарт", "max": "Макс"}
    plan_prices = {"mini": 399, "standard": 890, "max": 1990}

    plan_name = plan_names.get(plan, plan)
    price = plan_prices.get(plan, 0)

    await callback.message.edit_text(
        f"💳 <b>Оплата хостинга</b>\n\n"
        f"Тариф: <b>{plan_name}</b>\n"
        f"Цена: <b>{price} ₽/мес</b>\n\n"
        f"🔜 Оплата через ЮMoney и Telegram Stars будет доступна в следующем обновлении.\n\n"
        f"Напиши в поддержку для ручной активации: @botify_support",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stop_bot:"))
async def stop_bot(callback: CallbackQuery):
    await callback.answer("⏸️ Бот остановлен (функция в разработке)", show_alert=True)


@router.callback_query(F.data.startswith("start_bot:"))
async def start_bot(callback: CallbackQuery):
    await callback.answer("▶️ Бот запущен (функция в разработке)", show_alert=True)


@router.callback_query(F.data.startswith("restart_bot:"))
async def restart_bot(callback: CallbackQuery):
    await callback.answer("🔄 Бот перезапущен (функция в разработке)", show_alert=True)
