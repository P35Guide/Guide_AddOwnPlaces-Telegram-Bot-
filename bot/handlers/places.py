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

from bot.keyboard import action_keyboard
from bot.model.place import Place
from bot.services.api_client import add_custom_place, get_all_custom_places, get_custom_place_by_id
from bot.states import AddPlace
from bot.utils.logger import logger
from aiogram.types import InputFile
import base64
from io import BytesIO
from bot.utils.logger import logger
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📌 Додати своє місце")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Вітаю!\n\nЩо бажаєш зробити?\n- Додати своє місце\n- Переглянути всі місця",
        reply_markup=kb
    )
    await state.clear()

@router.message(F.text == "📌 Додати своє місце")
async def add_place_handler(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.username} ({message.from_user.id}) pressed 'Add your place' button")
    await message.answer("Введи назву місця:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddPlace.wait_for_title)


@router.message(F.text == "👀 Подивитись додані місця")
async def view_custom_places_handler(message: Message):
    async with aiohttp.ClientSession() as session:
        places = await get_all_custom_places(session)

    if not places:
        await message.answer("Список місць порожній або сервер недоступний.", reply_markup=action_keyboard())
        return

    keyboard_rows = []
    for place in places:
        if not isinstance(place, dict):
            continue

        place_id = place.get("id") if place.get("id") is not None else place.get("Id")
        title = place.get("nameOfPlace") or "Без назви"

        if place_id is None:
            continue

        keyboard_rows.append([
            InlineKeyboardButton(text=title[:40], callback_data=f"custom_place_view:{place_id}")
        ])

    if not keyboard_rows:
        await message.answer("Не вдалося сформувати список місць.", reply_markup=action_keyboard())
        return

    await message.answer(
        f"✅ Знайдено {len(keyboard_rows)} місць:\nОберіть заклад:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )


@router.callback_query(F.data.startswith("custom_place_view:"))
async def custom_place_details_handler(callback: CallbackQuery):
    
    raw_id = callback.data.split(":", maxsplit=1)[1]

    try:
        place_id = int(raw_id)
    except ValueError:
        await callback.answer("Некоректний ідентифікатор місця", show_alert=True)
        return

    async with aiohttp.ClientSession() as session:
        place = await get_custom_place_by_id(place_id, session)

    if not place:
        await callback.answer("⚠️ Місце не знайдено", show_alert=True)
        return

    title = place.get("nameOfPlace") or "Без назви"
    address = place.get("address") or "Адреса не вказана"
    description = place.get("description") or "Опис відсутній"

    # Надсилаємо текстову інформацію
    await callback.message.answer(
        f"🏢 <b>{title}</b>\n"
        f"📌 <b>Адреса:</b> {address}\n"
        f"📝 <b>Про місце:</b> {description}",
        parse_mode="HTML"
    )

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
    await state.update_data(title=message.text)
    await message.answer("Введи опис місця:")
    await state.set_state(AddPlace.wait_for_discription)


@router.message(AddPlace.wait_for_discription)
async def add_discription(message: Message, state: FSMContext):
    await state.update_data(discription=message.text)
    await message.answer("Введи адресу місця:")
    await state.set_state(AddPlace.wait_for_shor_adress)


@router.message(AddPlace.wait_for_shor_adress)
async def add_adress(message: Message, state: FSMContext):
    address = message.text or ""
    if len(address) < 5 or not all(char.isalnum() or char in ",. -" for char in address):
        await message.answer("Адреса має бути не менше 5 символів і містити лише літери, цифри, пробіли, коми, крапки та дефіси. Спробуйте ще раз.")
        return

    await state.update_data(adress=address)
    # Ask user how to provide coordinates
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Передати мої координати"), KeyboardButton(text="Передати геомітку")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Як бажаєш передати координати місця?\n\n- 'Передати мої координати' — використати твоє поточне місцезнаходження.\n- 'Передати геомітку' — надішли геомітку на карті.",
        reply_markup=kb
    )
    await state.set_state(AddPlace.wait_for_coords_choice)

# --- Coordinates handlers ---
@router.message(AddPlace.wait_for_coords_choice, F.text.in_(["Передати мої координати", "Передати геомітку"]))
async def coords_choice_handler(message: Message, state: FSMContext):
    if message.text == "Передати мої координати":
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Відправити мої координати", request_location=True)]],
            resize_keyboard=True
        )
        await message.answer("Натисни кнопку нижче, щоб надіслати свої координати:", reply_markup=kb)
        await state.set_state(AddPlace.wait_for_coords)
    else:
        await message.answer(
            "Щоб надіслати геомітку місця:\n\n1. Натисни скріпку 📎 в полі введення повідомлення.\n2. Обери 'Місцезнаходження'.\n3. Натисни 'Вказати місце на карті'.\n4. Перемісти мітку на потрібне місце та надішли.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(AddPlace.wait_for_coords)

@router.message(AddPlace.wait_for_coords, F.location)
async def receive_coords(message: Message, state: FSMContext):
    latitude = message.location.latitude
    longitude = message.location.longitude
    await state.update_data(latitude=latitude, longitude=longitude)
    await message.answer("Координати отримано! Тепер надай 5 фото місцевості, по одному:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddPlace.wait_for_foto)

@router.message(AddPlace.wait_for_coords)
async def coords_fallback(message: Message, state: FSMContext):
    await message.answer(
        "Будь ласка, надішли геомітку місця або скористайся кнопкою для надсилання своїх координат.\n\nЯкщо не знаєш як це зробити,\n\n1. Натисни скріпку 📎 в полі введення повідомлення.\n2. Обери 'Місцезнаходження'.\n3. Натисни 'Вказати місце на карті'.\n4. Перемісти мітку на потрібне місце та надішли."
    )

@router.message(AddPlace.wait_for_foto, F.photo)
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos_ids = data.get("photos", [])
    photos_ids.append(message.photo[-1].file_id)
    await state.update_data(photos=photos_ids)

    number_photo = len(photos_ids)
    if number_photo < 5:
        await message.answer(f"Фото отримано ({number_photo}/5). Надішли ще {5 - number_photo} фото.")
        return

    confirm_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Так"), KeyboardButton(text="Ні")]],
        resize_keyboard=True
    )
    await message.answer("Всі фото отримано. Підтвердити додавання місця?", reply_markup=confirm_kb)
    await state.set_state(AddPlace.wait_for_confirm)


@router.message(AddPlace.wait_for_confirm, F.text.in_(["Так", "Ні"]))
async def confirm_add_place(message: Message, state: FSMContext, bot: Bot):

    logger.info(f"[DEBUG] confirm_add_place handler triggered. message.text={message.text}")
    await message.answer("Дякую!", reply_markup=ReplyKeyboardRemove())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📌 Додати своє місце")]],
        resize_keyboard=True
    )
    if message.text == "Так":
        adding_msg = await message.answer("Додавання місця...")
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
        # Видаляємо повідомлення 'Додавання місця...'
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=adding_msg.message_id)
        except Exception as e:
            logger.error(f"Failed to delete 'Adding place...' message: {e}")
        if result:
            logger.info("Place added successfully!")
            await message.answer("Місце додано!", reply_markup=kb)
        else:
            logger.error("Error while adding place to backend.")
            await message.answer("Сталася помилка при додаванні місця.", reply_markup=kb)
    elif message.text == "Ні":
        logger.info("[DEBUG] 'No' button pressed")
        logger.info("User cancelled adding place (No)")
        logger.info("Adding place cancelled by user.")
        await message.answer("Додавання місця скасовано.", reply_markup=kb)
        await state.clear()
        return


@router.message(AddPlace.wait_for_confirm)
async def confirm_fallback(message: Message):
    await message.answer("Використовуйте кнопки 'Так' або 'Ні' для підтвердження.")


@router.message()
async def unhandled_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Невідомий запит. Скористайтесь /start для початку.")
