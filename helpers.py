from datetime import datetime, timedelta
from typing import Optional
import pytz
from bot.config import settings

TZ = pytz.timezone(settings.TIMEZONE)


def format_datetime(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        local = dt.astimezone(TZ)
        return local.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso_str


def format_giveaway(g: dict, participants_count: int = None) -> str:
    prize_emoji = {
        "gift": "🎁",
        "stars": "⭐",
        "nft": "🖼",
        "other": "📦"
    }.get(g.get("prize_type", "other"), "🎁")

    status_map = {
        "active": "🟢 Активен",
        "finished": "✅ Завершён",
        "cancelled": "🔴 Отменён"
    }
    status = status_map.get(g.get("status", "active"), g.get("status"))

    count = participants_count if participants_count is not None else g.get("participants_count", 0)

    text = (
        f"<b>{prize_emoji} {g['title']}</b>\n\n"
        f"📝 {g.get('description') or 'Без описания'}\n\n"
        f"🏆 Приз: <b>{g['prize_info']}</b>\n"
        f"👥 Победителей: <b>{g['winners_count']}</b>\n"
        f"👤 Участников: <b>{count}</b>\n"
        f"⏰ Итоги: <b>{format_datetime(g['end_at'])}</b>\n"
        f"📊 Статус: {status}\n"
    )

    if g.get("status") == "finished" and g.get("winners_json"):
        import json
        try:
            winners = json.loads(g["winners_json"])
            text += f"\n🏅 Победители ID: {', '.join(map(str, winners))}"
        except Exception:
            pass

    return text


def parse_end_date(text: str) -> Optional[datetime]:
    """
    Accepts:
    - DD.MM.YYYY HH:MM
    - DD.MM.YYYY
    - +Nh / +Nd (relative)
    Returns UTC datetime or None
    """
    text = text.strip().lower()
    now = datetime.now(TZ)

    # Relative: +2h, +1d, +30m
    if text.startswith("+"):
        try:
            value = text[1:]
            if value.endswith("h"):
                delta = timedelta(hours=int(value[:-1]))
            elif value.endswith("d"):
                delta = timedelta(days=int(value[:-1]))
            elif value.endswith("m"):
                delta = timedelta(minutes=int(value[:-1]))
            else:
                return None
            local = now + delta
            return local.astimezone(pytz.UTC).replace(tzinfo=None)
        except Exception:
            return None

    # Absolute
    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            local = TZ.localize(datetime.strptime(text, fmt))
            if local <= now:
                return None  # past
            return local.astimezone(pytz.UTC).replace(tzinfo=None)
        except ValueError:
            continue
    return None
