from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    get_user, save_dialogue_message, get_dialogue_history,
    clear_dialogue, deduct_credits, create_bot_record
)
from keyboards import (
    cancel_dialogue_keyboard, confirm_creation_keyboard,
    back_to_menu_keyboard, main_menu_keyboard
)
from ai_client import ask_ai, detect_summary, extract_cost, extract_bot_type, SYSTEM_PROMPT_BOT, SYSTEM_PROMPT_MINIAPP
from config import BOT_COSTS

router = Router()


class CreateBotStates(StatesGroup):
    dialogue = State()
    confirm = State()


@router.callback_query(F.data == "create_bot")
async def start_create_bot(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Произошла ошибка. Попробуй /start")
        return

    credits = user["credits"]
    min_cost = BOT_COSTS["simple"]

    if credits < min_cost:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно кредитов</b>\n\n"
            f"У тебя: <b>{credits} кредитов</b>\n"
            f"Минимум для создания бота: <b>{min_cost} кредитов</b>\n\n"
            f"Пополни баланс в разделе 💳 Кредиты",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await clear_dialogue(callback.from_user.id)
    await state.set_state(CreateBotStates.dialogue)
    await state.update_data(bot_type_context="bot", pending_summary=None, pending_cost=None)

    await callback.message.edit_text(
        "🤖 <b>Создание Telegram-бота</b>\n\n"
        "Опиши, какой бот тебе нужен — ИИ задаст уточняющие вопросы и подготовит всё необходимое.\n\n"
        "<i>Например: «Хочу бота для барбершопа с записью к мастеру»</i>",
        reply_markup=cancel_dialogue_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "create_miniapp")
async def start_create_miniapp(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Произошла ошибка. Попробуй /start")
        return

    credits = user["credits"]
    min_cost = BOT_COSTS["miniapp_simple"]

    if credits < min_cost:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно кредитов</b>\n\n"
            f"У тебя: <b>{credits} кредитов</b>\n"
            f"Минимум для Mini App: <b>{min_cost} кредитов</b>",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await clear_dialogue(callback.from_user.id)
    await state.set_state(CreateBotStates.dialogue)
    await state.update_data(bot_type_context="miniapp", pending_summary=None, pending_cost=None)

    await callback.message.edit_text(
        "📱 <b>Создание Telegram Mini App</b>\n\n"
        "Опиши, какое веб-приложение тебе нужно внутри Telegram — ИИ задаст уточняющие вопросы.\n\n"
        "<i>Например: «Интернет-магазин одежды с корзиной и оплатой»</i>",
        reply_markup=cancel_dialogue_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateBotStates.dialogue)
async def handle_dialogue_message(message: Message, state: FSMContext):
    data = await state.get_data()
    is_miniapp = data.get("bot_type_context") == "miniapp"
    system = SYSTEM_PROMPT_MINIAPP if is_miniapp else SYSTEM_PROMPT_BOT

    user_id = message.from_user.id
    user_text = message.text

    await save_dialogue_message(user_id, "user", user_text)

    history = await get_dialogue_history(user_id, limit=20)
    ai_messages = [{"role": m["role"], "content": m["content"]} for m in history]

    thinking_msg = await message.answer("🤔 ИИ думает...")

    try:
        ai_response = await ask_ai(ai_messages, system=system)
    except Exception as e:
        await thinking_msg.delete()
        await message.answer(
            "❌ Ошибка связи с ИИ. Попробуй ещё раз.",
            reply_markup=cancel_dialogue_keyboard(),
        )
        return

    await save_dialogue_message(user_id, "assistant", ai_response)
    await thinking_msg.delete()

    if detect_summary(ai_response):
        cost = extract_cost(ai_response)
        bot_type = extract_bot_type(cost)

        user = await get_user(user_id)
        credits = user["credits"] if user else 0

        await state.update_data(pending_summary=ai_response, pending_cost=cost, pending_bot_type=bot_type)
        await state.set_state(CreateBotStates.confirm)

        suffix = ""
        if credits < cost:
            suffix = f"\n\n⚠️ У тебя <b>{credits} кредитов</b>, нужно <b>{cost}</b>. Пополни баланс в разделе 💳 Кредиты."

        await message.answer(
            f"{ai_response}{suffix}",
            reply_markup=confirm_creation_keyboard(cost, bot_type) if credits >= cost else back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            ai_response,
            reply_markup=cancel_dialogue_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("confirm_create:"))
async def confirm_creation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cost = data.get("pending_cost", 300)
    summary = data.get("pending_summary", "")
    bot_type = data.get("pending_bot_type", "medium")

    user_id = callback.from_user.id
    user = await get_user(user_id)

    success = await deduct_credits(user_id, cost, f"Создание бота ({bot_type})")
    if not success:
        await callback.answer("❌ Недостаточно кредитов!", show_alert=True)
        return

    import re
    name_match = re.search(r"Название:\s*(.+)", summary)
    bot_name = name_match.group(1).strip() if name_match else "Мой бот"

    bot_id = await create_bot_record(user["id"], bot_name, bot_type, summary)
    await clear_dialogue(user_id)
    await state.clear()

    remaining = user["credits"] - cost

    await callback.message.edit_text(
        f"✅ <b>Бот создан!</b>\n\n"
        f"🤖 Название: <b>{bot_name}</b>\n"
        f"📋 Тип: <b>{bot_type}</b>\n"
        f"💳 Списано: <b>{cost} кредитов</b>\n"
        f"💰 Остаток: <b>{remaining} кредитов</b>\n\n"
        f"Бот сохранён в разделе 📦 <b>Мои боты</b>.\n"
        f"Там ты сможешь скачать код или запустить хостинг.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_dialogue")
async def cancel_dialogue(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_dialogue(callback.from_user.id)
    await callback.message.edit_text(
        "❌ <b>Создание отменено</b>\n\nВернись в главное меню, чтобы начать заново.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
