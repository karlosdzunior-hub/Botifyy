from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_user, get_transaction_history
from keyboards import credits_keyboard, buy_credits_keyboard, back_to_menu_keyboard

router = Router()

TRANSACTION_ICONS = {
    "bonus": "🎁",
    "referral": "👥",
    "spend": "💸",
    "top_up": "💳",
}


@router.callback_query(F.data == "credits")
async def show_credits(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    credits = user["credits"] if user else 0

    text = (
        f"💳 <b>Кредиты</b>\n\n"
        f"💰 Баланс: <b>{credits} кредитов</b>\n\n"
        f"📊 <b>Стоимость создания:</b>\n"
        f"• Простой бот (команды, меню) — 150 кредитов\n"
        f"• Средний бот (логика, БД) — 300 кредитов\n"
        f"• Сложный бот (API, оплата) — 600 кредитов\n"
        f"• Mini App простой — 400 кредитов\n"
        f"• Mini App сложный — 800 кредитов\n"
        f"• Доработка бота — 100 кредитов\n\n"
        f"💡 Диалог и исправление ошибок — <b>бесплатно</b>"
    )

    await callback.message.edit_text(text, reply_markup=credits_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "buy_credits")
async def show_buy_credits(callback: CallbackQuery):
    await callback.message.edit_text(
        "💳 <b>Пополнить баланс</b>\n\n"
        "Выбери пакет кредитов:\n\n"
        "🔜 Оплата через ЮMoney и Telegram Stars будет доступна в следующем обновлении.\n\n"
        "Для пополнения напиши в поддержку: @botify_support",
        reply_markup=buy_credits_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery):
    amount = callback.data.split(":")[1]
    await callback.answer(
        f"🔜 Оплата {amount} кредитов будет доступна скоро. Напиши @botify_support",
        show_alert=True,
    )


@router.callback_query(F.data == "credit_history")
async def show_credit_history(callback: CallbackQuery):
    transactions = await get_transaction_history(callback.from_user.id, limit=10)

    if not transactions:
        await callback.message.edit_text(
            "📋 <b>История транзакций</b>\n\nПока нет транзакций.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    lines = ["📋 <b>История транзакций</b>\n"]
    for t in transactions:
        icon = TRANSACTION_ICONS.get(t["type"], "🔹")
        amount = t["amount"]
        sign = "+" if amount > 0 else ""
        date = t["created_at"][:10] if t["created_at"] else ""
        desc = t["description"] or ""
        lines.append(f"{icon} {sign}{amount} кр. — {desc} <i>({date})</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
