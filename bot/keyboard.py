from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def action_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📌 Додати своє місце")],
        [KeyboardButton(text="👀 Подивитись додані місця")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)