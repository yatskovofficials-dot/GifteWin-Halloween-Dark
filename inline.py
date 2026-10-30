from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import settings


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Создать розыгрыш", callback_data="create_giveaway")
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Активные розыгрыши", callback_data="active_giveaways"),
        InlineKeyboardButton(text="📋 Мои розыгрыши", callback_data="my_giveaways")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="🏆 Топ удачи", callback_data="top_luck")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="referral")
    )
    builder.row(
        InlineKeyboardButton(
            text="📢 Канал GifteWin",
            url=settings.CHANNEL_LINK
        )
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
    )
    return builder.as_markup()


def prize_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Подарок (Gift)", callback_data="prize_gift"),
        InlineKeyboardButton(text="⭐ Звёзды (Stars)", callback_data="prize_stars")
    )
    builder.row(
        InlineKeyboardButton(text="🖼 NFT / Collectible", callback_data="prize_nft"),
        InlineKeyboardButton(text="📦 Другое", callback_data="prize_other")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_main")
    )
    return builder.as_markup()


def winners_count_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=str(i), callback_data=f"winners_{i}"))
    builder.adjust(5)
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="create_giveaway"))
    return builder.as_markup()


def confirm_giveaway_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Создать розыгрыш", callback_data="confirm_create"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_main")
    )
    return builder.as_markup()


def giveaway_actions_kb(giveaway_id: int, is_creator: bool = False, is_joined: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_joined:
        builder.row(
            InlineKeyboardButton(text="🎯 Участвовать", callback_data=f"join_{giveaway_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Вы уже участвуете", callback_data="already_joined")
        )

    builder.row(
        InlineKeyboardButton(text="👥 Участники", callback_data=f"participants_{giveaway_id}"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"view_{giveaway_id}")
    )

    if is_creator:
        builder.row(
            InlineKeyboardButton(text="🚫 Отменить розыгрыш", callback_data=f"cancel_{giveaway_id}")
        )

    builder.row(
        InlineKeyboardButton(text="📢 Канал", url=settings.CHANNEL_LINK),
        InlineKeyboardButton(text="« В меню", callback_data="back_main")
    )
    return builder.as_markup()


def active_giveaways_kb(giveaways: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in giveaways[:15]:
        emoji = {"gift": "🎁", "stars": "⭐", "nft": "🖼", "other": "📦"}.get(g.get("prize_type", "other"), "🎁")
        title = g["title"][:28] + ("…" if len(g["title"]) > 28 else "")
        count = g.get("participants_count", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {title} · {count} чел.",
                callback_data=f"view_{g['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« В меню", callback_data="back_main"))
    return builder.as_markup()


def my_giveaways_kb(giveaways: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    status_emoji = {"active": "🟢", "finished": "✅", "cancelled": "🔴"}
    for g in giveaways[:15]:
        emoji = status_emoji.get(g["status"], "⚪")
        title = g["title"][:25] + ("…" if len(g["title"]) > 25 else "")
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {title}",
                callback_data=f"view_{g['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« В меню", callback_data="back_main"))
    return builder.as_markup()


def back_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« В главное меню", callback_data="back_main"))
    return builder.as_markup()


def channel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📢 Открыть канал GifteWin",
            url=settings.CHANNEL_LINK
        )
    )
    builder.row(InlineKeyboardButton(text="« В меню", callback_data="back_main"))
    return builder.as_markup()


def share_referral_kb(ref_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            switch_inline_query=f"Присоединяйся к GifteWin RANDOM и участвуй в розыгрышах подарков! {ref_link}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="📢 Канал", url=settings.CHANNEL_LINK),
        InlineKeyboardButton(text="« В меню", callback_data="back_main")
    )
    return builder.as_markup()


def cancel_confirm_kb(giveaway_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel_{giveaway_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"view_{giveaway_id}")
    )
    return builder.as_markup()
