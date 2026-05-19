from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.deep_linking import create_start_link

from database import get_user, get_referral_count, get_referral_earnings
from keyboards import referrals_keyboard
from config import REFERRAL_BONUS

router = Router()


@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка. Попробуй /start")
        return

    ref_count = await get_referral_count(callback.from_user.id)
    ref_earnings = await get_referral_earnings(callback.from_user.id)

    bot = callback.bot
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"

    text = (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей и получай бонусные кредиты!\n\n"
        f"🎁 За каждого приглашённого: <b>+{REFERRAL_BONUS} кредитов</b>\n\n"
        f"📊 <b>Твоя статистика:</b>\n"
        f"• Приглашено друзей: <b>{ref_count}</b>\n"
        f"• Заработано кредитов: <b>{ref_earnings}</b>\n\n"
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"Скопируй и отправь другу — когда он зарегистрируется, "
        f"вы оба получите бонус!"
    )

    await callback.message.edit_text(text, reply_markup=referrals_keyboard(), parse_mode="HTML")
    await callback.answer()
