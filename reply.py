from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
