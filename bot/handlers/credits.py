from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from aiogram.filters import Command

from database import get_user, get_transaction_history, add_credits, get_user_by_telegram_id
from keyboards import (
    credits_keyboard, buy_credits_keyboard,
    payment_method_keyboard, back_to_menu_keyboard,
)
from payments import CREDIT_PACKAGES, send_stars_invoice, build_yoomoney_url, get_package
from config import YOOMONEY_WALLET, BOT_USERNAME

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
        f"• Простой бот — 150 кредитов\n"
        f"• Средний бот — 300 кредитов\n"
        f"• Сложный бот — 600 кредитов\n"
        f"• Mini App простой — 400 кредитов\n"
        f"• Mini App сложный — 800 кредитов\n"
        f"• Доработка бота — 100 кредитов\n\n"
        f"💡 Диалог и исправление ошибок — <b>бесплатно</b>"
    )
    await callback.message.edit_text(text, reply_markup=credits_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "buy_credits")
async def show_buy_credits(callback: CallbackQuery):
    lines = ["💳 <b>Пополнить баланс</b>\n\nВыбери пакет кредитов:\n"]
    for pkg in CREDIT_PACKAGES:
        lines.append(
            f"{pkg['label']}: <b>{pkg['credits']} кредитов</b>\n"
            f"   ⭐ {pkg['stars']} Stars  |  💵 {pkg['rub']} ₽\n"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=buy_credits_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def choose_payment_method(callback: CallbackQuery):
    credits = int(callback.data.split(":")[1])
    pkg = get_package(credits)
    if not pkg:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"💳 <b>{pkg['label']} — {credits} кредитов</b>\n\n"
        f"Выбери способ оплаты:\n\n"
        f"⭐ <b>Telegram Stars</b> — {pkg['stars']} Stars\n"
        f"💵 <b>ЮMoney</b> — {pkg['rub']} ₽",
        reply_markup=payment_method_keyboard(credits, pkg["stars"], pkg["rub"]),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_with_stars(callback: CallbackQuery, bot: Bot):
    credits = int(callback.data.split(":")[1])
    await send_stars_invoice(bot, callback.from_user.id, credits)
    await callback.answer()


@router.callback_query(F.data.startswith("pay_yoomoney:"))
async def pay_with_yoomoney(callback: CallbackQuery):
    credits = int(callback.data.split(":")[1])
    pkg = get_package(credits)
    if not pkg:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    if not YOOMONEY_WALLET:
        await callback.answer("ЮMoney временно недоступна. Используй Telegram Stars.", show_alert=True)
        return

    url = build_yoomoney_url(
        wallet=YOOMONEY_WALLET,
        telegram_id=callback.from_user.id,
        credits=credits,
        rub=pkg["rub"],
        bot_username=BOT_USERNAME,
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"💳 Оплатить {pkg['rub']} ₽ через ЮMoney", url=url))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"buy:{credits}"))

    await callback.message.edit_text(
        f"💵 <b>Оплата через ЮMoney</b>\n\n"
        f"Пакет: <b>{pkg['label']}</b> — {credits} кредитов\n"
        f"Сумма: <b>{pkg['rub']} ₽</b>\n\n"
        f"1. Нажми кнопку ниже\n"
        f"2. Оплати на сайте ЮMoney\n"
        f"3. Кредиты зачислятся <b>автоматически</b> в течение минуты",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_stars_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("credits:"):
        return

    credits = int(payload.split(":")[1])
    stars = message.successful_payment.total_amount
    telegram_id = message.from_user.id

    await add_credits(
        telegram_id,
        credits,
        f"Telegram Stars ({stars} ⭐)",
        t_type="top_up",
    )

    user = await get_user(telegram_id)
    balance = user["credits"] if user else credits

    await message.answer(
        f"✅ <b>Оплата Stars прошла!</b>\n\n"
        f"⭐ Потрачено: <b>{stars} Stars</b>\n"
        f"💰 Зачислено: <b>+{credits} кредитов</b>\n"
        f"📊 Баланс: <b>{balance} кредитов</b>\n\n"
        f"Готов создавать ботов! 🤖",
        parse_mode="HTML",
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
