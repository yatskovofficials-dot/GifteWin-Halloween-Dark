from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime
import json

from bot.database import db
from bot.states.giveaway import CreateGiveaway
from bot.keyboards.inline import (
    prize_type_kb, winners_count_kb, confirm_giveaway_kb,
    giveaway_actions_kb, active_giveaways_kb, my_giveaways_kb,
    back_main_kb, cancel_confirm_kb, main_menu_kb
)
from bot.utils.helpers import format_giveaway, format_datetime, parse_end_date
from bot.utils.random_draw import draw_winners
from bot.config import settings

router = Router(name="giveaway")


# ==================== CREATE FLOW ====================

@router.callback_query(F.data == "create_giveaway")
async def start_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateGiveaway.prize_type)
    await callback.message.edit_text(
        "<b>🎁 Создание розыгрыша</b>\n\n"
        "Выбери тип приза:",
        reply_markup=prize_type_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prize_"), CreateGiveaway.prize_type)
async def set_prize_type(callback: CallbackQuery, state: FSMContext):
    prize_type = callback.data.replace("prize_", "")
    await state.update_data(prize_type=prize_type)
    await state.set_state(CreateGiveaway.title)
    await callback.message.edit_text(
        "<b>📝 Название розыгрыша</b>\n\n"
        "Напиши короткое и понятное название (до 60 символов):\n"
        "<i>Пример: Разыгрываю редкий NFT-подарок</i>",
        reply_markup=back_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateGiveaway.title)
async def set_title(message: Message, state: FSMContext):
    title = message.text.strip()[:60]
    if len(title) < 3:
        await message.answer("Название слишком короткое. Минимум 3 символа.")
        return
    await state.update_data(title=title)
    await state.set_state(CreateGiveaway.description)
    await message.answer(
        "<b>📄 Описание</b>\n\n"
        "Добавь описание розыгрыша (условия, что нужно сделать и т.д.):\n"
        "<i>Можно пропустить — отправь «-»</i>",
        parse_mode="HTML"
    )


@router.message(CreateGiveaway.description)
async def set_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == "-":
        desc = ""
    await state.update_data(description=desc[:500])
    await state.set_state(CreateGiveaway.prize_info)
    await message.answer(
        "<b>🏆 Детали приза</b>\n\n"
        "Опиши приз максимально точно:\n"
        "• Для подарка: название + модель/фон\n"
        "• Для звёзд: количество\n"
        "• Для NFT: коллекция + ID\n\n"
        "<i>Пример: Collectible Gift «Durov’s Cap» #0420</i>",
        parse_mode="HTML"
    )


@router.message(CreateGiveaway.prize_info)
async def set_prize_info(message: Message, state: FSMContext):
    prize_info = message.text.strip()[:200]
    if len(prize_info) < 2:
        await message.answer("Слишком коротко. Укажи детали приза.")
        return
    await state.update_data(prize_info=prize_info)
    await state.set_state(CreateGiveaway.winners_count)
    await message.answer(
        "<b>👥 Количество победителей</b>\n\n"
        "Сколько человек выиграет?",
        reply_markup=winners_count_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("winners_"), CreateGiveaway.winners_count)
async def set_winners(callback: CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[1])
    await state.update_data(winners_count=count)
    await state.set_state(CreateGiveaway.end_date)
    await callback.message.edit_text(
        "<b>⏰ Дата и время итогов</b>\n\n"
        "Укажи, когда подвести итоги:\n\n"
        "• <code>25.12.2025 20:00</code>\n"
        "• <code>+2h</code> (через 2 часа)\n"
        "• <code>+1d</code> (через 1 день)\n"
        "• <code>+30m</code> (через 30 минут)\n\n"
        f"Часовой пояс: <b>{settings.TIMEZONE}</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateGiveaway.end_date)
async def set_end_date(message: Message, state: FSMContext):
    end_dt = parse_end_date(message.text)
    if not end_dt:
        await message.answer(
            "❌ Неверный формат или дата в прошлом.\n"
            "Попробуй ещё раз:\n"
            "<code>25.12.2025 20:00</code> или <code>+2h</code>",
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    await state.update_data(end_at=end_dt.isoformat())

    prize_emoji = {"gift": "🎁", "stars": "⭐", "nft": "🖼", "other": "📦"}.get(data["prize_type"], "🎁")

    preview = (
        f"<b>📋 Предпросмотр розыгрыша</b>\n\n"
        f"{prize_emoji} <b>{data['title']}</b>\n"
        f"{data.get('description') or 'Без описания'}\n\n"
        f"🏆 Приз: <b>{data['prize_info']}</b>\n"
        f"👥 Победителей: <b>{data['winners_count']}</b>\n"
        f"⏰ Итоги: <b>{format_datetime(end_dt.isoformat())}</b>\n\n"
        f"Всё верно?"
    )
    await state.set_state(CreateGiveaway.confirm)
    await message.answer(preview, reply_markup=confirm_giveaway_kb(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_create", CreateGiveaway.confirm)
async def confirm_create(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    giveaway_id = await db.create_giveaway(
        creator_id=user_id,
        title=data["title"],
        description=data.get("description", ""),
        prize_type=data["prize_type"],
        prize_info=data["prize_info"],
        winners_count=data["winners_count"],
        min_participants=settings.MIN_PARTICIPANTS,
        end_at=data["end_at"]
    )

    await state.clear()

    g = await db.get_giveaway(giveaway_id)
    text = format_giveaway(g, participants_count=0)
    text += "\n\n✅ <b>Розыгрыш создан!</b>\nПоделись ссылкой с друзьями."

    await callback.message.edit_text(
        text,
        reply_markup=giveaway_actions_kb(giveaway_id, is_creator=True, is_joined=False),
        parse_mode="HTML"
    )
    await callback.answer("Розыгрыш создан! 🎉")


# ==================== VIEW & JOIN ====================

@router.callback_query(F.data == "active_giveaways")
async def list_active(callback: CallbackQuery):
    giveaways = await db.get_active_giveaways(20)
    if not giveaways:
        await callback.message.edit_text(
            "😔 Пока нет активных розыгрышей.\n\nСоздай первый!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>🔥 Активные розыгрыши</b> ({len(giveaways)})\n\nВыбери розыгрыш:",
            reply_markup=active_giveaways_kb(giveaways),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "my_giveaways")
async def list_my(callback: CallbackQuery):
    giveaways = await db.get_user_giveaways(callback.from_user.id)
    if not giveaways:
        await callback.message.edit_text(
            "У тебя пока нет розыгрышей.\nСоздай первый!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"<b>📋 Твои розыгрыши</b> ({len(giveaways)})",
            reply_markup=my_giveaways_kb(giveaways),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("view_"))
async def view_giveaway(callback: CallbackQuery):
    try:
        gid = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    g = await db.get_giveaway(gid)
    if not g:
        await callback.answer("Розыгрыш не найден", show_alert=True)
        return

    count = await db.get_participants_count(gid)
    is_creator = g["creator_id"] == callback.from_user.id
    is_joined = await db.is_participant(gid, callback.from_user.id)

    text = format_giveaway(g, participants_count=count)

    # Show top participants preview with chance
    participants = await db.get_participants(gid)
    if participants:
        total_weight = sum(100 + (p.get("luck_at_join") or 0) for p in participants)
        text += "\n\n<b>👥 Участники (шанс):</b>\n"
        for i, p in enumerate(participants[:8], 1):
            luck = p.get("luck_at_join") or 0
            weight = 100 + luck
            chance = (weight / total_weight * 100) if total_weight else 0
            name = f"@{p['username']}" if p.get("username") else p.get("full_name") or f"ID{p['user_id']}"
            text += f"{i}. {name} — <b>{chance:.1f}%</b> (🍀{luck})\n"
        if len(participants) > 8:
            text += f"<i>…и ещё {len(participants) - 8}</i>\n"

    await callback.message.edit_text(
        text,
        reply_markup=giveaway_actions_kb(gid, is_creator=is_creator, is_joined=is_joined),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("join_"))
async def join_giveaway(callback: CallbackQuery):
    try:
        gid = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    g = await db.get_giveaway(gid)
    if not g or g["status"] != "active":
        await callback.answer("Розыгрыш уже завершён или отменён", show_alert=True)
        return

    # Optional: require channel boost / subscription check can be added here
    success = await db.join_giveaway(gid, callback.from_user.id)
    if success:
        await callback.answer("✅ Ты в деле! Удачи 🍀", show_alert=True)
        # Refresh view
        callback.data = f"view_{gid}"
        await view_giveaway(callback)
    else:
        await callback.answer("Ты уже участвуешь", show_alert=True)


@router.callback_query(F.data == "already_joined")
async def already_joined(callback: CallbackQuery):
    await callback.answer("Ты уже в списке участников 👍", show_alert=False)


@router.callback_query(F.data.startswith("participants_"))
async def show_participants(callback: CallbackQuery):
    try:
        gid = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    participants = await db.get_participants(gid)
    if not participants:
        await callback.answer("Пока никого нет", show_alert=True)
        return

    total_weight = sum(100 + (p.get("luck_at_join") or 0) for p in participants)
    text = f"<b>👥 Участники розыгрыша #{gid}</b>\n\n"
    for i, p in enumerate(participants[:30], 1):
        luck = p.get("luck_at_join") or 0
        weight = 100 + luck
        chance = (weight / total_weight * 100) if total_weight else 0
        name = f"@{p['username']}" if p.get("username") else (p.get("full_name") or f"ID{p['user_id']}")
        text += f"{i}. {name} — <b>{chance:.1f}%</b> 🍀{luck}\n"

    if len(participants) > 30:
        text += f"\n…и ещё {len(participants) - 30} участников"

    await callback.message.edit_text(
        text,
        reply_markup=back_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_prompt(callback: CallbackQuery):
    try:
        gid = int(callback.data.split("_")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    g = await db.get_giveaway(gid)
    if not g or g["creator_id"] != callback.from_user.id:
        await callback.answer("Это не твой розыгрыш", show_alert=True)
        return

    await callback.message.edit_text(
        f"Точно отменить розыгрыш <b>«{g['title']}»</b>?\n\nЭто действие нельзя отменить.",
        reply_markup=cancel_confirm_kb(gid),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel(callback: CallbackQuery):
    try:
        gid = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Ошибка", show_alert=True)
        return

    success = await db.cancel_giveaway(gid, callback.from_user.id)
    if success:
        await callback.message.edit_text(
            "🔴 Розыгрыш отменён.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        await callback.answer("Отменено")
    else:
        await callback.answer("Не удалось отменить", show_alert=True)
