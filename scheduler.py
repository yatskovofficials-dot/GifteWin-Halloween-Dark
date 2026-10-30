from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from aiogram import Bot

from bot.database import db
from bot.utils.random_draw import draw_winners
from bot.utils.helpers import format_datetime
from bot.config import settings

scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)


async def process_expired_giveaways(bot: Bot):
    """Check and finish expired giveaways every minute"""
    try:
        expired = await db.get_expired_giveaways()
        for g in expired:
            participants = await db.get_participants(g["id"])
            winners_count = g["winners_count"]

            if len(participants) < g.get("min_participants", 2):
                # Not enough participants — cancel or finish empty
                await db.finish_giveaway(g["id"], [])
                try:
                    await bot.send_message(
                        g["creator_id"],
                        f"⚠️ Розыгрыш <b>«{g['title']}»</b> завершён без победителей — "
                        f"недостаточно участников ({len(participants)}).",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                logger.info(f"Giveaway {g['id']} finished with 0 winners (not enough participants)")
                continue

            winners = draw_winners(participants, winners_count)
            await db.finish_giveaway(g["id"], winners)

            # Notify creator
            winners_text = ""
            for i, wid in enumerate(winners, 1):
                user = await db.get_user(wid)
                name = f"@{user['username']}" if user and user.get("username") else f"ID {wid}"
                winners_text += f"{i}. {name}\n"

            try:
                await bot.send_message(
                    g["creator_id"],
                    f"🎉 <b>Итоги розыгрыша «{g['title']}»</b>\n\n"
                    f"🏆 Победители:\n{winners_text}\n"
                    f"Не забудь передать приз!",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify creator {g['creator_id']}: {e}")

            # Notify winners
            for wid in winners:
                try:
                    await bot.send_message(
                        wid,
                        f"🎊 <b>Поздравляем!</b>\n\n"
                        f"Ты выиграл в розыгрыше <b>«{g['title']}»</b>!\n"
                        f"Приз: <b>{g['prize_info']}</b>\n\n"
                        f"Свяжись с организатором для получения приза.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            logger.info(f"Giveaway {g['id']} finished. Winners: {winners}")
    except Exception as e:
        logger.error(f"Error processing expired giveaways: {e}")


def start_scheduler(bot: Bot):
    scheduler.add_job(
        process_expired_giveaways,
        trigger=IntervalTrigger(seconds=30),
        args=[bot],
        id="finish_giveaways",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started")
