from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_user_bots
from keyboards import back_to_menu_keyboard, my_bots_keyboard

router = Router()


@router.callback_query(F.data == "hosting")
async def show_hosting(callback: CallbackQuery):
    bots = await get_user_bots(callback.from_user.id)

    text = (
        "🖥️ <b>Хостинг</b>\n\n"
        "📦 Тарифы:\n\n"
        "🟢 <b>Мини</b> — 399 ₽/мес\n"
        "   1 бот • до 2 000 пользователей\n"
        "   Автоперезапуск при падении\n\n"
        "🔵 <b>Стандарт</b> — 890 ₽/мес\n"
        "   3 бота • до 20 000 пользователей\n"
        "   Автоперезапуск + статистика\n\n"
        "🟣 <b>Макс</b> — 1 990 ₽/мес\n"
        "   10 ботов • безлимит\n"
        "   Всё выше + приоритетная поддержка\n\n"
        "ℹ️ Хостинг независим от кредитов — оплачивается отдельно.\n\n"
    )

    if bots:
        text += "Выбери бота из списка, чтобы подключить хостинг:"
        await callback.message.edit_text(text, reply_markup=my_bots_keyboard(bots), parse_mode="HTML")
    else:
        text += "Сначала создай бота в разделе 🤖 <b>Создать бота</b>."
        await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard(), parse_mode="HTML")

    await callback.answer()
