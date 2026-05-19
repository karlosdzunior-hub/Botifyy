from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_or_create_user, get_user
from keyboards import main_menu_keyboard
from config import WELCOME_CREDITS

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
        except ValueError:
            pass

    user, is_new = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        referrer_id=referrer_id,
    )

    if is_new:
        text = (
            f"👋 Добро пожаловать в <b>Botify</b>!\n\n"
            f"Создай своего Telegram-бота без знания кода — просто опиши что нужно, "
            f"а ИИ всё сделает сам.\n\n"
            f"🎁 Тебе начислено <b>{WELCOME_CREDITS} приветственных кредитов</b> — хватит на первого бота!\n\n"
            f"💰 Баланс: <b>{WELCOME_CREDITS} кредитов</b>"
        )
    else:
        credits = user["credits"]
        text = (
            f"👋 С возвращением, <b>{message.from_user.first_name}</b>!\n\n"
            f"💰 Баланс: <b>{credits} кредитов</b>"
        )

    await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user(callback.from_user.id)
    credits = user["credits"] if user else 0

    text = (
        f"🏠 <b>Главное меню</b>\n\n"
        f"💰 Баланс: <b>{credits} кредитов</b>\n\n"
        f"Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
