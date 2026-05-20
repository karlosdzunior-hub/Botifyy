from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

from database import (
    get_user, save_dialogue_message, get_dialogue_history,
    clear_dialogue, deduct_credits, create_bot_record, update_bot_status
)
from keyboards import (
    cancel_dialogue_keyboard, confirm_creation_keyboard,
    back_to_menu_keyboard, main_menu_keyboard
)
from ai_client import (
    ask_ai, detect_summary, extract_cost, extract_bot_type,
    SYSTEM_PROMPT_BOT, SYSTEM_PROMPT_MINIAPP
)
from code_generator import generate_bot_code, fix_bot_code, check_syntax, save_bot_code
from config import BOT_COSTS

router = Router()

MAX_FIX_CYCLES = 3


class CreateBotStates(StatesGroup):
    dialogue = State()
    waiting_token = State()
    confirm = State()


@router.callback_query(F.data == "create_bot")
async def start_create_bot(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Произошла ошибка. Попробуй /start")
        return

    if user["credits"] < BOT_COSTS["simple"]:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно кредитов</b>\n\n"
            f"У тебя: <b>{user['credits']} кредитов</b>\n"
            f"Минимум: <b>{BOT_COSTS['simple']} кредитов</b>\n\n"
            f"Пополни баланс в разделе 💳 Кредиты",
            reply_markup=back_to_menu_keyboard(), parse_mode="HTML",
        )
        await callback.answer()
        return

    await clear_dialogue(callback.from_user.id)
    await state.set_state(CreateBotStates.dialogue)
    await state.update_data(bot_type_context="bot")

    await callback.message.edit_text(
        "🤖 <b>Создание Telegram-бота</b>\n\n"
        "Опиши, какой бот тебе нужен — ИИ задаст уточняющие вопросы.\n\n"
        "<i>Например: «Хочу бота для барбершопа с записью к мастеру»</i>",
        reply_markup=cancel_dialogue_keyboard(), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "create_miniapp")
async def start_create_miniapp(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Произошла ошибка. Попробуй /start")
        return

    if user["credits"] < BOT_COSTS["miniapp_simple"]:
        await callback.message.edit_text(
            f"❌ <b>Недостаточно кредитов</b>\n\nМинимум: <b>{BOT_COSTS['miniapp_simple']} кредитов</b>",
            reply_markup=back_to_menu_keyboard(), parse_mode="HTML",
        )
        await callback.answer()
        return

    await clear_dialogue(callback.from_user.id)
    await state.set_state(CreateBotStates.dialogue)
    await state.update_data(bot_type_context="miniapp")

    await callback.message.edit_text(
        "📱 <b>Создание Telegram Mini App</b>\n\n"
        "Опиши, какое веб-приложение тебе нужно внутри Telegram.\n\n"
        "<i>Например: «Интернет-магазин одежды с корзиной и оплатой»</i>",
        reply_markup=cancel_dialogue_keyboard(), parse_mode="HTML",
    )
    await callback.answer()


@router.message(CreateBotStates.dialogue)
async def handle_dialogue_message(message: Message, state: FSMContext):
    data = await state.get_data()
    is_miniapp = data.get("bot_type_context") == "miniapp"
    system = SYSTEM_PROMPT_MINIAPP if is_miniapp else SYSTEM_PROMPT_BOT
    user_id = message.from_user.id

    await save_dialogue_message(user_id, "user", message.text)
    history = await get_dialogue_history(user_id, limit=20)
    ai_messages = [{"role": m["role"], "content": m["content"]} for m in history]

    thinking = await message.answer("🤔 ИИ думает...")
    try:
        ai_response = await ask_ai(ai_messages, system=system)
    except Exception:
        await thinking.delete()
        await message.answer("❌ Ошибка связи с ИИ. Попробуй ещё раз.", reply_markup=cancel_dialogue_keyboard())
        return

    await save_dialogue_message(user_id, "assistant", ai_response)
    await thinking.delete()

    if detect_summary(ai_response):
        cost = extract_cost(ai_response)
        bot_type = extract_bot_type(cost)
        user = await get_user(user_id)
        credits = user["credits"] if user else 0

        await state.update_data(pending_summary=ai_response, pending_cost=cost, pending_bot_type=bot_type)
        await state.set_state(CreateBotStates.confirm)

        suffix = f"\n\n⚠️ У тебя <b>{credits} кредитов</b>, нужно <b>{cost}</b>." if credits < cost else ""
        await message.answer(
            f"{ai_response}{suffix}",
            reply_markup=confirm_creation_keyboard(cost, bot_type) if credits >= cost else back_to_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(ai_response, reply_markup=cancel_dialogue_keyboard(), parse_mode="HTML")


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
    await state.update_data(current_bot_id=bot_id, current_bot_name=bot_name, current_summary=summary)

    await callback.message.edit_text(
        f"✅ <b>Требования зафиксированы!</b>\n\n"
        f"🤖 Бот: <b>{bot_name}</b>\n"
        f"💳 Списано: <b>{cost} кредитов</b>\n\n"
        f"Теперь введи <b>Bot Token</b> от @BotFather для нового бота.\n"
        f"Это нужно чтобы запустить его:\n\n"
        f"<code>1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ</code>",
        reply_markup=cancel_dialogue_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(CreateBotStates.waiting_token)
    await callback.answer()


@router.message(CreateBotStates.waiting_token)
async def handle_bot_token(message: Message, state: FSMContext):
    token = message.text.strip()
    import re
    if not re.match(r"^\d+:[A-Za-z0-9_-]{35,}$", token):
        await message.answer(
            "❌ Неверный формат токена. Токен выглядит так:\n"
            "<code>1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ</code>\n\n"
            "Получи его у @BotFather командой /newbot",
            reply_markup=cancel_dialogue_keyboard(),
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    bot_id = data.get("current_bot_id")
    bot_name = data.get("current_bot_name", "Мой бот")
    summary = data.get("current_summary", "")

    from database import save_bot_token
    await save_bot_token(bot_id, token)

    gen_msg = await message.answer(
        f"⚙️ <b>Генерирую код бота «{bot_name}»...</b>\n\n"
        f"ИИ пишет код · проверяю синтаксис · исправляю ошибки\n\n"
        f"Обычно это занимает 15–30 секунд.",
        parse_mode="HTML",
    )

    code = None
    error_log = None

    for attempt in range(1, MAX_FIX_CYCLES + 1):
        try:
            if attempt == 1:
                await gen_msg.edit_text(
                    f"⚙️ <b>Генерирую код... ({attempt}/{MAX_FIX_CYCLES})</b>",
                    parse_mode="HTML",
                )
                code = await generate_bot_code(summary, bot_name)
            else:
                await gen_msg.edit_text(
                    f"🔧 <b>Исправляю ошибки... (попытка {attempt}/{MAX_FIX_CYCLES})</b>",
                    parse_mode="HTML",
                )
                code = await fix_bot_code(code, error_log, attempt)

            ok, error = check_syntax(code)
            if ok:
                break
            error_log = error

        except Exception as e:
            error_log = str(e)

    if not code:
        await gen_msg.delete()
        await message.answer(
            "❌ <b>Не удалось сгенерировать код.</b>\n\nПожалуйста, свяжись с поддержкой: @botify_support",
            reply_markup=main_menu_keyboard(), parse_mode="HTML",
        )
        await state.clear()
        return

    ok, _ = check_syntax(code)
    code_path = save_bot_code(bot_id, code, bot_name)
    await update_bot_status(bot_id, "created", code)

    await gen_msg.delete()
    await state.clear()

    code_bytes = code.encode("utf-8")
    file = BufferedInputFile(code_bytes, filename=f"{bot_name.replace(' ', '_')}_bot.py")

    status_icon = "✅" if ok else "⚠️"
    status_text = "Синтаксис проверен" if ok else "Возможны мелкие ошибки — проверь вручную"

    await message.answer_document(
        file,
        caption=(
            f"🤖 <b>Бот «{bot_name}» готов!</b>\n\n"
            f"{status_icon} {status_text}\n\n"
            f"<b>Как запустить:</b>\n"
            f"1. Установи зависимости: <code>pip install aiogram==3.13.0</code>\n"
            f"2. Запусти: <code>BOT_TOKEN={token[:10]}... python bot.py</code>\n\n"
            f"Или перейди в 📦 Мои боты → Захостить — и бот запустится автоматически на сервере."
        ),
        parse_mode="HTML",
    )
    await message.answer(
        "Что хочешь сделать дальше?",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "cancel_dialogue")
async def cancel_dialogue(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await clear_dialogue(callback.from_user.id)
    await callback.message.edit_text(
        "❌ <b>Отменено.</b>",
        reply_markup=main_menu_keyboard(), parse_mode="HTML",
    )
    await callback.answer()
