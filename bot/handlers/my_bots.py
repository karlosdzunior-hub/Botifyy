from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile

from database import get_user_bots, get_bot, get_user, update_bot_status, get_hosting_record
from keyboards import my_bots_keyboard, bot_detail_keyboard, hosting_plans_keyboard, back_to_menu_keyboard
from process_manager import (
    start_bot_process, stop_bot_process, get_process_status, get_process_logs
)
from docker_manager import (
    stop_bot_container, start_bot_container, restart_bot_container,
    get_container_status, get_container_logs, is_docker_available
)
from code_generator import get_bot_code_path

router = Router()

STATUS_LABELS = {
    "created": "✅ Создан (код готов)",
    "running": "🟡 Запущен (активен пока бот онлайн)",
    "hosted": "🟢 Захощен 24/7",
    "stopped": "🔴 Остановлен",
    "error": "⚠️ Ошибка",
}
TYPE_LABELS = {
    "simple": "Простой бот",
    "medium": "Средний бот",
    "complex": "Сложный бот",
    "miniapp_simple": "Mini App (простой)",
    "miniapp_complex": "Mini App (сложный)",
}


@router.callback_query(F.data == "my_bots")
async def show_my_bots(callback: CallbackQuery):
    bots = await get_user_bots(callback.from_user.id)
    if not bots:
        await callback.message.edit_text(
            "📦 <b>Мои боты</b>\n\nУ тебя пока нет ботов.\nНажми 🤖 <b>Создать бота</b>!",
            reply_markup=back_to_menu_keyboard(), parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📦 <b>Мои боты</b> — {len(bots)} шт.\n\nВыбери бота:",
        reply_markup=my_bots_keyboard(bots), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bot_detail:"))
async def show_bot_detail(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    status = bot["status"]

    if status == "running":
        proc_status = get_process_status(bot_id)
        if proc_status != "running":
            status = "stopped"
            await update_bot_status(bot_id, "stopped")

    container_info = ""
    if status == "hosted":
        docker_status = await get_container_status(bot_id)
        container_info = f"\n🐳 Контейнер: <b>{docker_status}</b>"

    hosting = await get_hosting_record(bot_id)
    hosting_info = ""
    if hosting:
        hosting_info = f"\n💳 Тариф: <b>{hosting['plan'].capitalize()}</b>\n📅 До: <b>{hosting['expires_at'][:10]}</b>"

    status_label = STATUS_LABELS.get(status, status)
    bot_type = TYPE_LABELS.get(bot["bot_type"], bot["bot_type"])
    created_at = bot["created_at"][:10] if bot["created_at"] else "—"

    text = (
        f"🤖 <b>{bot['name']}</b>\n\n"
        f"📋 Тип: {bot_type}\n"
        f"🔹 Статус: {status_label}{container_info}{hosting_info}\n"
        f"📅 Создан: {created_at}"
    )

    has_code = get_bot_code_path(bot_id) is not None or bot.get("description")

    await callback.message.edit_text(
        text,
        reply_markup=bot_detail_keyboard(bot_id, status=status, has_code=has_code),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("run_process:"))
async def run_process(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    if not bot.get("bot_token"):
        await callback.answer("❌ Токен бота не задан. Пересоздай бота.", show_alert=True)
        return

    code_path = get_bot_code_path(bot_id)
    if not code_path and bot.get("description"):
        from code_generator import save_bot_code
        try:
            code_path = save_bot_code(bot_id, bot["description"], bot["name"])
        except Exception as e:
            await callback.answer(f"❌ Не удалось восстановить код: {e}", show_alert=True)
            return

    if not code_path:
        await callback.answer("❌ Код бота не найден. Пересоздай бота.", show_alert=True)
        return

    msg = await callback.message.edit_text(
        f"⚙️ <b>Запускаю бота «{bot['name']}»...</b>\n\nУстанавливаю зависимости — это займёт 15–30 сек.",
        parse_mode="HTML",
    )

    success, result = await start_bot_process(bot_id, bot["bot_token"])

    if success:
        await update_bot_status(bot_id, "running")
        await msg.edit_text(
            f"🟡 <b>Бот «{bot['name']}» запущен!</b>\n\n"
            f"⚡ Режим: активен пока Botify онлайн\n"
            f"🔢 PID: <code>{result}</code>\n\n"
            f"Для работы 24/7 нажми <b>Захостить 24/7</b>.",
            reply_markup=bot_detail_keyboard(bot_id, status="running", has_code=True),
            parse_mode="HTML",
        )
    else:
        await msg.edit_text(
            f"❌ <b>Не удалось запустить бота</b>\n\n<code>{result}</code>",
            reply_markup=bot_detail_keyboard(bot_id, status="created", has_code=has_code),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("stop_process:"))
async def stop_process(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    ok = await stop_bot_process(bot_id)
    if ok:
        await update_bot_status(bot_id, "stopped")
        await callback.answer(f"⏸️ Бот «{bot['name']}» остановлен", show_alert=True)
    else:
        await callback.answer("❌ Не удалось остановить", show_alert=True)


@router.callback_query(F.data.startswith("logs_process:"))
async def logs_process(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    logs = get_process_logs(bot_id, lines=30)
    if not logs.strip():
        logs = "Логи пустые"
    await callback.message.answer(
        f"📋 <b>Логи бота (последние 30 строк):</b>\n\n<pre>{logs[:3000]}</pre>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("download_code:"))
async def download_code(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    code_path = get_bot_code_path(bot_id)
    code = None

    if code_path:
        with open(code_path, "rb") as f:
            code = f.read()
    elif bot.get("description"):
        code = bot["description"].encode("utf-8")

    if not code:
        await callback.answer("Код не найден", show_alert=True)
        return

    filename = f"{bot['name'].replace(' ', '_')}_bot.py"
    file = BufferedInputFile(code, filename=filename)
    await callback.message.answer_document(
        file,
        caption=f"📥 Код бота <b>{bot['name']}</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("host_bot:"))
async def show_hosting_plans(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)

    if not bot or not (get_bot_code_path(bot_id) or bot.get("description")):
        await callback.answer("❌ Код бота не найден", show_alert=True)
        return

    if not bot.get("bot_token"):
        await callback.answer("❌ Токен бота не задан. Пересоздай бота.", show_alert=True)
        return

    await callback.message.edit_text(
        f"🖥️ <b>Хостинг 24/7 для «{bot['name']}»</b>\n\n"
        f"Бот будет работать круглосуточно в Docker-контейнере.\n\n"
        f"🟢 <b>Мини</b> — 399 ₽/мес · 1 бот · до 2 000 пользователей\n\n"
        f"🔵 <b>Стандарт</b> — 890 ₽/мес · 3 бота · до 20 000 пользователей\n\n"
        f"🟣 <b>Макс</b> — 1 990 ₽/мес · 10 ботов · безлимит",
        reply_markup=hosting_plans_keyboard(bot_id), parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_hosting:"))
async def activate_hosting(callback: CallbackQuery):
    parts = callback.data.split(":")
    bot_id = int(parts[1])
    plan = parts[2]

    bot = await get_bot(bot_id)
    if not bot:
        await callback.answer("Бот не найден", show_alert=True)
        return

    plan_names = {"mini": "Мини", "standard": "Стандарт", "max": "Макс"}
    plan_prices = {"mini": 399, "standard": 890, "max": 1990}
    plan_name = plan_names.get(plan, plan)
    price = plan_prices.get(plan, 0)

    if not is_docker_available():
        await callback.message.edit_text(
            f"⚠️ <b>Docker недоступен на сервере</b>\n\n"
            f"Пока используй бесплатный запуск через кнопку <b>▶️ Запустить</b>.",
            reply_markup=back_to_menu_keyboard(), parse_mode="HTML",
        )
        await callback.answer()
        return

    user = await get_user(callback.from_user.id)
    launch_msg = await callback.message.edit_text(
        f"🚀 <b>Захожу бота «{bot['name']}» на 24/7...</b>\n\nЭто займёт 30–60 секунд.",
        parse_mode="HTML",
    )

    from docker_manager import build_and_run_bot
    from database import activate_hosting as db_activate_hosting

    success, result = await build_and_run_bot(bot_id, bot["bot_token"])

    if success:
        await db_activate_hosting(user["id"], bot_id, plan)
        await update_bot_status(bot_id, "hosted")
        await launch_msg.edit_text(
            f"✅ <b>Бот «{bot['name']}» захощен 24/7!</b>\n\n"
            f"🐳 Контейнер: <code>{result}</code>\n"
            f"💳 Тариф: <b>{plan_name}</b> — {price} ₽/мес\n\n"
            f"Бот работает круглосуточно. При падении — автоматически перезапустится.",
            reply_markup=back_to_menu_keyboard(), parse_mode="HTML",
        )
    else:
        await launch_msg.edit_text(
            f"❌ <b>Ошибка запуска Docker</b>\n\n<code>{result}</code>\n\n"
            f"Используй бесплатный режим — кнопка <b>▶️ Запустить</b>.",
            reply_markup=bot_detail_keyboard(bot_id, status=bot["status"], has_code=True),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("stop_bot:"))
async def stop_bot(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    await stop_bot_container(bot_id)
    await update_bot_status(bot_id, "stopped")
    await callback.answer(f"⏸️ Бот «{bot['name']}» остановлен", show_alert=True)


@router.callback_query(F.data.startswith("start_bot:"))
async def start_bot(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    ok = await start_bot_container(bot_id)
    if ok:
        await update_bot_status(bot_id, "hosted")
        await callback.answer(f"▶️ Бот «{bot['name']}» запущен", show_alert=True)
    else:
        await callback.answer("❌ Не удалось запустить Docker-контейнер.", show_alert=True)


@router.callback_query(F.data.startswith("restart_bot:"))
async def restart_bot(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    bot = await get_bot(bot_id)
    ok = await restart_bot_container(bot_id)
    await callback.answer(
        f"🔄 Бот «{bot['name']}» {'перезапущен' if ok else 'не смог перезапуститься'}",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("logs_bot:"))
async def show_logs(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    logs = await get_container_logs(bot_id, lines=30)
    if not logs.strip():
        logs = "Логи пустые"
    await callback.message.answer(
        f"📋 <b>Логи бота (последние 30 строк):</b>\n\n<pre>{logs[:3000]}</pre>",
        parse_mode="HTML",
    )
    await callback.answer()
