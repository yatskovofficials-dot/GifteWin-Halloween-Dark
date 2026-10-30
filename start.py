from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from bot.database import db
from bot.keyboards.inline import main_menu_kb, channel_kb, back_main_kb
from bot.config import settings

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split(maxsplit=1)
    referrer_id = None

    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
        except ValueError:
            referrer_id = None

    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referrer_id=referrer_id
    )

    welcome = (
        f"<b>🎁 GifteWin RANDOM</b>\n\n"
        f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"Здесь ты можешь:\n"
        f"• Создавать розыгрыши своих <b>подарков</b>, <b>NFT</b> и <b>звёзд</b>\n"
        f"• Участвовать в чужих розыгрышах\n"
        f"• Получать <b>баллы удачи</b> за рефералов и повышать шансы\n\n"
        f"🎲 Победители выбираются честно и случайно с учётом баллов удачи.\n\n"
        f"Удачи! 🍀"
    )

    await message.answer(welcome, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.message(Command("menu"))
@router.callback_query(F.data == "back_main")
async def show_main_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "<b>🎁 GifteWin RANDOM</b>\n\n"
        "Главное меню. Выбери действие:"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "help")
async def help_handler(callback: CallbackQuery):
    text = (
        "<b>ℹ️ Помощь — GifteWin RANDOM</b>\n\n"
        "<b>Как создать розыгрыш:</b>\n"
        "1. Нажми «Создать розыгрыш»\n"
        "2. Выбери тип приза (подарок / звёзды / NFT)\n"
        "3. Укажи название, описание и детали приза\n"
        "4. Выбери количество победителей\n"
        "5. Укажи дату и время подведения итогов\n"
        "6. Подтверди создание\n\n"
        "<b>Как участвовать:</b>\n"
        "Открой активный розыгрыш и нажми «Участвовать».\n\n"
        "<b>Баллы удачи:</b>\n"
        f"За каждого приглашённого друга ты получаешь <b>+{settings.REFERRAL_BONUS_BALLS}</b> баллов удачи.\n"
        "Чем больше баллов — тем выше шанс выиграть.\n\n"
        "<b>Важно:</b>\n"
        "• Бот только проводит розыгрыш. Передача приза — ответственность создателя.\n"
        "• Итоги подводятся автоматически в указанное время.\n"
        "• Минимальное количество участников можно задать при создании.\n\n"
        f"📢 Канал проекта: {settings.CHANNEL_LINK}"
    )
    await callback.message.edit_text(text, reply_markup=channel_kb(), parse_mode="HTML")
    await callback.answer()


@router.message(Command("channel"))
async def channel_cmd(message: Message):
    await message.answer(
        f"📢 Наш канал: <b>{settings.CHANNEL_LINK}</b>\n\n"
        "Там публикуются все крупные розыгрыши и новости!",
        reply_markup=channel_kb(),
        parse_mode="HTML"
    )
