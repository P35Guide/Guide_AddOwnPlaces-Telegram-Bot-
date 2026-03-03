import base64
import aiohttp
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.keyboard import action_keyboard, coords_choice_keyboard, location_keyboard, confirm_keyboard, language_selection_keyboard, get_language_code_from_display
from bot.model.place import Place
from bot.services.api_client import add_custom_place, get_all_custom_places, get_custom_place_by_id
from bot.states import AddPlace, LanguageSelection
from bot.utils.logger import logger
from bot.utils.i18n import i18n
from aiogram.types import InputFile
from io import BytesIO

router = Router()

def normalize_lang(lang: str) -> str:
    """Нормалізувати мовний код"""
    return i18n.normalize_lang(lang)


def get_base_lang(user_id: int, telegram_lang: str) -> str:
    return i18n.get_user_language(user_id, fallback_lang=normalize_lang(telegram_lang))

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = get_base_lang(user_id, message.from_user.language_code or "uk")
    
    logger.info(f"User {message.from_user.username} ({user_id}) started the bot with language {user_lang}")
    
    # Запитати в користувача, чи задовільна його мова
    language_display_names = {
        "uk": "Українська 🇺🇦",
        "en": "English 🇬🇧",
        "de": "Deutsch 🇩🇪",
        "fr": "Français 🇫🇷",
        "es": "Español 🇪🇸",
        "it": "Italiano 🇮🇹",
        "pl": "Polski 🇵🇱",
        "pt": "Português 🇵🇹",
        "ja": "日本語 🇯🇵",
        "zh": "中文 🇨🇳",
    }
    
    user_lang_display = language_display_names.get(user_lang, "Українська 🇺🇦")
    
    await message.answer(
        i18n.get("language_confirm", user_lang, lang_display=user_lang_display),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=i18n.get("yes", user_lang))],
                [KeyboardButton(text=i18n.get("no", user_lang))]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(LanguageSelection.waiting_for_confirmation)
    await state.update_data(detected_lang=user_lang)

# Обробник для відповіді на питання про мову при старту
@router.message(LanguageSelection.waiting_for_confirmation)
async def handle_language_confirmation(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    yes_variants = i18n.get_all_buttons_variants("yes")
    
    if message.text in yes_variants:
        # Користувач задоволений своєю мовою
        i18n.set_user_language(message.from_user.id, user_lang)
        await message.answer(
            i18n.get("start_greeting", user_lang),
            reply_markup=action_keyboard(user_lang)
        )
        await state.clear()
    else:
        # Користувач хоче змінити мову
        await message.answer(
            i18n.get("language_selection_title", user_lang),
            reply_markup=language_selection_keyboard()
        )
        await state.set_state(LanguageSelection.waiting_for_language)
        await state.update_data(detected_lang=user_lang)

# Обробник для вибору мови в меню
@router.message(LanguageSelection.waiting_for_language)
async def handle_language_selection(message: Message, state: FSMContext):
    lang_code = get_language_code_from_display(message.text)
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    
    if lang_code:
        # Зберігаємо вибрану мову
        i18n.set_user_language(message.from_user.id, lang_code)
        await message.answer(
            i18n.get("language_selected", lang_code, language=message.text),
            reply_markup=action_keyboard(lang_code)
        )
        await state.clear()
    else:
        await message.answer(
            i18n.get("language_selection_title", user_lang),
            reply_markup=language_selection_keyboard()
        )

@router.message(F.text.contains("🌐"))
async def change_language_handler(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    logger.info(f"User {message.from_user.username} ({message.from_user.id}) wants to change language")
    
    await message.answer(
        i18n.get("language_selection_title", user_lang),
        reply_markup=language_selection_keyboard()
    )
    await state.set_state(LanguageSelection.waiting_for_language)

@router.message(F.text.contains("📌"))
async def add_place_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_lang = get_base_lang(user_id, message.from_user.language_code or "uk")
    
    logger.info(f"User {message.from_user.username} ({user_id}) pressed 'Add your place' button")
    await message.answer(i18n.get("enter_title", user_lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddPlace.wait_for_title)

@router.message(F.text.contains("👀"))
async def view_custom_places_handler(message: Message):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    
    async with aiohttp.ClientSession() as session:
        places = await get_all_custom_places(session)

    if not places:
        await message.answer(i18n.get("empty_list", user_lang), reply_markup=action_keyboard(user_lang))
        return

    keyboard_rows = []
    for place in places:
        if not isinstance(place, dict):
            continue

        place_id = place.get("id") if place.get("id") is not None else place.get("Id")
        title = place.get("nameOfPlace") or i18n.get("no_title", user_lang)

        if place_id is None:
            continue

        keyboard_rows.append([
            InlineKeyboardButton(text=title[:40], callback_data=f"custom_place_view:{place_id}")
        ])

    if not keyboard_rows:
        await message.answer(i18n.get("list_build_error", user_lang), reply_markup=action_keyboard(user_lang))
        return

    await message.answer(
        i18n.get("places_found", user_lang, count=len(keyboard_rows)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("custom_place_view:"))
async def custom_place_details_handler(callback: CallbackQuery):
    user_lang = get_base_lang(callback.from_user.id, callback.from_user.language_code or "uk")
    
    raw_id = callback.data.split(":", maxsplit=1)[1]

    try:
        place_id = int(raw_id)
    except ValueError:
        await callback.answer(i18n.get("incorrect_id", user_lang), show_alert=True)
        return

    async with aiohttp.ClientSession() as session:
        place = await get_custom_place_by_id(place_id, session)

    if not place:
        await callback.answer(i18n.get("place_not_found", user_lang), show_alert=True)
        return

    title = place.get("nameOfPlace") or i18n.get("no_title", user_lang)
    address = place.get("address") or i18n.get("no_address", user_lang)
    description = place.get("description") or i18n.get("no_description", user_lang)

    place_info = (
        i18n.get("place_title", user_lang, title=title) + "\n" +
        i18n.get("place_address", user_lang, address=address) + "\n" +
        i18n.get("place_description", user_lang, description=description)
    )
    
    await callback.message.answer(place_info, parse_mode="HTML")

    # Відправляємо всі 5 фото
    photos_base64 = [
        place.get("photo1"),
        place.get("photo2"),
        place.get("photo3"),
        place.get("photo4"),
        place.get("photo5")
    ]
    media_group = []

    for index, encoded_photo in enumerate(photos_base64, start=1):
        if not encoded_photo:
            continue

        try:
            photo_bytes = base64.b64decode(encoded_photo)
            media_group.append(
                InputMediaPhoto(
                    media=BufferedInputFile(photo_bytes, filename=f"place_{place_id}_{index}.jpg")
                )
            )
        except Exception as e:
            logger.error(f"Failed to decode photo {index} for place {place_id}: {e}")

    if media_group:
        try:
            await callback.message.answer_media_group(media=media_group)
        except Exception as e:
            logger.error(f"Failed to send media group for place {place_id}: {e}")

    await callback.answer()

@router.message(AddPlace.wait_for_title)
async def add_title(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    await state.update_data(title=message.text, lang=user_lang)
    await message.answer(i18n.get("enter_description", user_lang))
    await state.set_state(AddPlace.wait_for_discription)

@router.message(AddPlace.wait_for_discription)
async def add_discription(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    await state.update_data(discription=message.text)
    await message.answer(i18n.get("enter_address", user_lang))
    await state.set_state(AddPlace.wait_for_shor_adress)

@router.message(AddPlace.wait_for_shor_adress)
async def add_adress(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    address = message.text or ""
    if len(address) < 5 or not all(char.isalnum() or char in ",. -" for char in address):
        await message.answer(i18n.get("address_invalid", user_lang))
        return

    await state.update_data(adress=address)
    kb = coords_choice_keyboard(user_lang)
    await message.answer(
        i18n.get("choose_coords_method", user_lang),
        reply_markup=kb
    )
    await state.set_state(AddPlace.wait_for_coords_choice)

# --- Coordinates handlers ---
@router.message(AddPlace.wait_for_coords_choice)
async def coords_choice_handler(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    send_coords_variants = i18n.get_all_buttons_variants("send_my_coords")
    
    if message.text in send_coords_variants:
        kb = location_keyboard(user_lang)
        await message.answer(i18n.get("click_to_send_coords", user_lang), reply_markup=kb)
        await state.set_state(AddPlace.wait_for_coords)
    else:
        await message.answer(
            i18n.get("geopoint_instructions", user_lang),
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(AddPlace.wait_for_coords)

@router.message(AddPlace.wait_for_coords, F.location)
async def receive_coords(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    latitude = message.location.latitude
    longitude = message.location.longitude
    await state.update_data(latitude=latitude, longitude=longitude)
    await message.answer(i18n.get("coords_received", user_lang), reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddPlace.wait_for_foto)

@router.message(AddPlace.wait_for_coords)
async def coords_fallback(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    await message.answer(i18n.get("coords_required", user_lang))

@router.message(AddPlace.wait_for_foto, F.photo)
async def add_photo(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    photos_ids = data.get("photos", [])
    photos_ids.append(message.photo[-1].file_id)
    await state.update_data(photos=photos_ids)

    number_photo = len(photos_ids)
    if number_photo < 5:
        remaining = 5 - number_photo
        await message.answer(
            i18n.get("photo_received", user_lang, current=number_photo, total=5, remaining=remaining)
        )
        return

    confirm_kb = confirm_keyboard(user_lang)
    await message.answer(i18n.get("confirm_add", user_lang), reply_markup=confirm_kb)
    await state.set_state(AddPlace.wait_for_confirm)

@router.message(AddPlace.wait_for_confirm)
async def confirm_add_place(message: Message, state: FSMContext, bot: Bot):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    data = await state.get_data()
    user_lang = data.get("lang", user_lang)
    
    yes_variants = i18n.get_all_buttons_variants("yes")
    no_variants = i18n.get_all_buttons_variants("no")
    
    logger.info(f"[DEBUG] confirm_add_place handler triggered. message.text={message.text}")
    await message.answer(i18n.get("thank_you", user_lang), reply_markup=ReplyKeyboardRemove())
    kb = action_keyboard(user_lang)
    
    if message.text in yes_variants:
        adding_msg = await message.answer(i18n.get("adding_place", user_lang))
        logger.info("[DEBUG] 'Yes' button pressed")
        logger.info("User confirmed adding place (Yes)")
        data = await state.get_data()
        encoded_photos = []
        for photo_id in data.get("photos", []):
            file = await bot.get_file(photo_id)
            photo_buffer = await bot.download_file(file.file_path)
            photo_bytes = photo_buffer.read()
            base64photo = base64.b64encode(photo_bytes).decode("utf-8")
            encoded_photos.append(base64photo)
        place = Place()
        place.NameOfPlace = data.get("title")
        place.Description = data.get("discription")
        place.Address = data.get("adress")
        place.Latitude = data.get("latitude", 0.0)
        place.Longitude = data.get("longitude", 0.0)
        place.Photo1 = encoded_photos[0]
        place.Photo2 = encoded_photos[1]
        place.Photo3 = encoded_photos[2]
        place.Photo4 = encoded_photos[3]
        place.Photo5 = encoded_photos[4]
        logger.info("Sending place to backend with data: "
            f"Name: {place.NameOfPlace}, "
            f"Address: {place.Address}, "
            f"Latitude: {place.Latitude}, Longitude: {place.Longitude}, "
            f"Description: {place.Description}, "
            f"Photo1: {place.Photo1[:30]}..., "
            f"Photo2: {place.Photo2[:30]}..., "
            f"Photo3: {place.Photo3[:30]}..., "
            f"Photo4: {place.Photo4[:30]}..., "
            f"Photo5: {place.Photo5[:30]}..."
        )
        logger.info("Request sent to backend...")
        async with aiohttp.ClientSession() as session:
            result = await add_custom_place(place, session)
        logger.info(f"Response received from backend: {result}")
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=adding_msg.message_id)
        except Exception as e:
            logger.error(f"Failed to delete 'Adding place...' message: {e}")
        if result:
            logger.info("Place added successfully!")
            await message.answer(i18n.get("place_added", user_lang), reply_markup=kb)
        else:
            logger.error("Error while adding place to backend.")
            await message.answer(i18n.get("place_error", user_lang), reply_markup=kb)
    elif message.text in no_variants:
        logger.info("[DEBUG] 'No' button pressed")
        logger.info("User cancelled adding place (No)")
        await message.answer(i18n.get("place_cancelled", user_lang), reply_markup=kb)
        await state.clear()
    else:
        await message.answer(i18n.get("confirm_required", user_lang))

@router.message()
async def unhandled_message(message: Message, state: FSMContext):
    user_lang = get_base_lang(message.from_user.id, message.from_user.language_code or "uk")
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(i18n.get("unknown_request", user_lang))
