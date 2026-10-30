from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.database import db
from bot.config import settings

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("stats"))
async def stats_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return

    # Simple stats
    async with db.conn.execute("SELECT COUNT(*) as c FROM users") as cur:
        users = (await cur.fetchone())["c"]
    async with db.conn.execute("SELECT COUNT(*) as c FROM giveaways WHERE status='active'") as cur:
        active = (await cur.fetchone())["c"]
    async with db.conn.execute("SELECT COUNT(*) as c FROM giveaways WHERE status='finished'") as cur:
        finished = (await cur.fetchone())["c"]
    async with db.conn.execute("SELECT COUNT(*) as c FROM participants") as cur:
        parts = (await cur.fetchone())["c"]

    text = (
        f"<b>📊 Статистика GifteWin</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"🟢 Активных розыгрышей: <b>{active}</b>\n"
        f"✅ Завершённых: <b>{finished}</b>\n"
        f"🎟 Участий: <b>{parts}</b>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("addballs"))
async def add_balls_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addballs <user_id> <amount>")
        return
    try:
        uid = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("Неверные числа")
        return

    new = await db.add_luck_balls(uid, amount)
    await message.answer(f"✅ Пользователю {uid} теперь {new} баллов удачи")
