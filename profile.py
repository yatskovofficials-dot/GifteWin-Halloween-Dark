from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.database import db
from bot.keyboards.inline import main_menu_kb, share_referral_kb, back_main_kb
from bot.config import settings

router = Router(name="profile")


@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка профиля", show_alert=True)
        return

    username = f"@{user['username']}" if user.get("username") else "не указан"
    text = (
        f"<b>👤 Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📛 Ник: {username}\n"
        f"🍀 Баллы удачи: <b>{user['luck_balls']}</b>\n"
        f"👥 Приглашено друзей: <b>{user['total_referrals']}</b>\n\n"
        f"Чем больше баллов удачи — тем выше шанс выиграть в любом розыгрыше.\n"
        f"Приглашай друзей и получай +{settings.REFERRAL_BONUS_BALLS} баллов за каждого!"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    ref_link = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{callback.from_user.id}"

    text = (
        f"<b>🔗 Реферальная программа</b>\n\n"
        f"Твоя ссылка:\n<code>{ref_link}</code>\n\n"
        f"🍀 За каждого друга, который перейдёт по ссылке, ты получаешь "
        f"<b>+{settings.REFERRAL_BONUS_BALLS} баллов удачи</b>.\n\n"
        f"Максимум баллов: <b>{settings.MAX_BALLS_PER_USER}</b>\n"
        f"Сейчас у тебя: <b>{user['luck_balls'] if user else 0}</b>\n\n"
        f"Баллы увеличивают твой шанс в каждом розыгрыше!"
    )
    await callback.message.edit_text(
        text,
        reply_markup=share_referral_kb(ref_link),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "top_luck")
async def top_luck_handler(callback: CallbackQuery):
    top = await db.get_top_users(10)
    if not top:
        text = "Пока никто не набрал баллы удачи."
    else:
        text = "<b>🏆 Топ удачи</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(top, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            name = f"@{u['username']}" if u.get("username") else (u.get("full_name") or f"ID{u['user_id']}")
            text += f"{medal} {name} — <b>{u['luck_balls']}</b> 🍀 ({u['total_referrals']} реф.)\n"

    await callback.message.edit_text(text, reply_markup=back_main_kb(), parse_mode="HTML")
    await callback.answer()
