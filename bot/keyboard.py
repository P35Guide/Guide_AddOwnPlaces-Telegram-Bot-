from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.utils.i18n import i18n


def action_keyboard(lang: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=i18n.get("add_place_btn", lang))],
        [KeyboardButton(text=i18n.get("view_places_btn", lang))],
        [KeyboardButton(text=i18n.get("change_language_btn", lang))],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def coords_choice_keyboard(lang: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=i18n.get("send_my_coords", lang)), KeyboardButton(text=i18n.get("send_geopoint", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def location_keyboard(lang: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=i18n.get("send_my_location", lang), request_location=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def confirm_keyboard(lang: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=i18n.get("yes", lang)), KeyboardButton(text=i18n.get("no", lang))]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def language_selection_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура для вибору мови"""
    languages = {
        "🇺🇦 Українська": "uk",
        "🇬🇧 English": "en",
        "🇩🇪 Deutsch": "de",
        "🇫🇷 Français": "fr",
        "🇪🇸 Español": "es",
        "🇮🇹 Italiano": "it",
        "🇵🇱 Polski": "pl",
        "🇵🇹 Português": "pt",
        "🇯🇵 日本語": "ja",
        "🇨🇳 中文": "zh",
    }
    keyboard = [[KeyboardButton(text=lang)] for lang in languages.keys()]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_language_code_from_display(display_text: str) -> str:
    """Отримати мовний код з тексту кнопки"""
    languages = {
        "🇺🇦 Українська": "uk",
        "🇬🇧 English": "en",
        "🇩🇪 Deutsch": "de",
        "🇫🇷 Français": "fr",
        "🇪🇸 Español": "es",
        "🇮🇹 Italiano": "it",
        "🇵🇱 Polski": "pl",
        "🇵🇹 Português": "pt",
        "🇯🇵 日本語": "ja",
        "🇨🇳 中文": "zh",
    }
    return languages.get(display_text, "uk")
