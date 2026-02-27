from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import base64
import aiohttp
from bot.states import AddPlace
from bot.model.place import Place
from bot.services.api_client import add_custom_place
from bot.utils.logger import logger

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📌 Додати своє місце")]],
        resize_keyboard=True
    )
    await message.answer(
        "Вітаю! Щоб додати своє місце, натисни кнопку нижче:",
        reply_markup=kb
    )
    await state.clear()

@router.message(F.text == "📌 Додати своє місце")
async def add_place_handler(message: Message, state: FSMContext):
    logger.info(f"User {message.from_user.username} ({message.from_user.id}) pressed 'Add your place' button")
    # Hide keyboard
    await message.answer('Введи назву місця:', reply_markup=ReplyKeyboardRemove())
    logger.info("Keyboard hidden, place adding started")
    await state.set_state(AddPlace.wait_for_title)

@router.message(AddPlace.wait_for_title)
async def add_title(message: Message, state: FSMContext):
    logger.info(f"Received place title: {message.text}")
    info = message.text
    await state.update_data(title=info)
    await message.answer("Введи опис місця:")
    await state.set_state(AddPlace.wait_for_discription)

@router.message(AddPlace.wait_for_discription)
async def add_discription(message: Message, state: FSMContext):
    logger.info(f"Received place description: {message.text}")
    info = message.text
    await state.update_data(discription=info)
    await message.answer("Введи адресу місця:")
    await state.set_state(AddPlace.wait_for_shor_adress)

@router.message(AddPlace.wait_for_shor_adress)
async def add_adress(message: Message, state: FSMContext):
    logger.info(f"Received place address: {message.text}")
    info = message.text
    # Simple address validation: length and allowed characters
    if len(info) < 5 or not all(c.isalnum() or c in ",. -" for c in info):
        await message.answer("Адреса має бути не менше 5 символів і містити лише літери, цифри, пробіли, коми, крапки та дефіси. Спробуйте ще раз.")
        return
    await state.update_data(adress=info)
    await message.answer("Надай 5 фото місцевості, по одному:")
    await state.set_state(AddPlace.wait_for_foto)

@router.message(AddPlace.wait_for_foto, F.photo)
async def add_photo(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"Received photo: {message.photo[-1].file_id}")
    data = await state.get_data()
    photos_ids = data.get("photos", [])
    photos_ids.append(message.photo[-1].file_id)
    await state.update_data(photos=photos_ids)
    number_photo = len(photos_ids)
    logger.info(f"Total number of photos: {number_photo}")
    if number_photo < 5:
        await message.answer(f"Фото отримано ({number_photo}/5). Надішли ще {5-number_photo} фото.")
        return
    confirm_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Так"), KeyboardButton(text="Ні")]],
        resize_keyboard=True
    )
    await message.answer("Всі фото отримано. Підтвердити додавання місця?", reply_markup=confirm_kb)
    logger.info("All photos received, confirmation buttons shown")
    await state.set_state(AddPlace.wait_for_confirm)

@router.message(AddPlace.wait_for_confirm, F.text.in_(["Так", "Ні"]))
async def confirm_add_place(message: Message, state: FSMContext, bot: Bot):
    logger.info(f"[DEBUG] confirm_add_place handler triggered. message.text={message.text}")
    await message.answer("Дякую!", reply_markup=ReplyKeyboardRemove())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📌 Додати своє місце")]],
        resize_keyboard=True
    )
    adding_msg = await message.answer("Додавання місця...")
    if message.text == "Так":
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
        place.Photo1 = encoded_photos[0]
        place.Photo2 = encoded_photos[1]
        place.Photo3 = encoded_photos[2]
        place.Photo4 = encoded_photos[3]
        place.Photo5 = encoded_photos[4]
        logger.info(f"Sending place to backend: {place.NameOfPlace}, {place.Address}")
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

# Fallback handler for AddPlace.wait_for_confirm state to log any text
@router.message(AddPlace.wait_for_confirm)
async def confirm_fallback(message: Message, state: FSMContext):
    logger.info(f"[DEBUG] confirm_fallback handler triggered. message.text={message.text}")
    await message.answer("Використовуйте кнопки 'Так' або 'Ні' для підтвердження.")

@router.message()
async def unhandled_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        logger.info(f"Unknown request: {message.text}")
        await message.answer("Невідомий запит. Скористайтесь /start для початку.")

@router.message(AddPlace.wait_for_title)
async def add_title(message: Message, state: FSMContext):
    info = message.text
    await state.update_data(title=info)
    data = await state.get_data()
    saved = data.get("title")
    if saved == info:
        logger.info("Title locally saved")
        await message.answer("[Назва збережена]\nВведи опис місця")
        await state.set_state(AddPlace.wait_for_discription)
    else:
        await message.answer("[помилка в збережені]")
        # send_main_menu(message)

@router.message(AddPlace.wait_for_discription)
async def add_discription(message: Message, state: FSMContext):
    info = message.text
    await state.update_data(discription=info)
    data = await state.get_data()
    saved = data.get("discription")
    if saved == info:
        logger.info("Description locally saved")
        await message.answer("[Опис збережений]\nВведи адресу місця")
        await state.set_state(AddPlace.wait_for_shor_adress)
    else:
        await message.answer("[помилка в збережені]")
        # send_main_menu(message)

@router.message(AddPlace.wait_for_shor_adress)
async def add_adress(message: Message, state: FSMContext):
    info = message.text
    await state.update_data(adress=info)
    data = await state.get_data()
    saved = data.get("adress")
    if saved == info:
        logger.info("Address locally saved")
        await message.answer("[Адреса збережена]\nНадай 5 фото місцевості")
        await state.set_state(AddPlace.wait_for_foto)
    else:
        await message.answer("[помилка в збережені]")
        # send_main_menu(message)

@router.message(AddPlace.wait_for_foto, F.photo)
async def add_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    photos_ids = data.get("photos", [])
    photos_ids.append(message.photo[-1].file_id)
    await state.update_data(photos=photos_ids)
    number_photo = len(photos_ids)
    if number_photo < 5:
        return
    encoded_photos = []
    for photo_id in photos_ids:
        file = await bot.get_file(photo_id)
        photo_buffer = await bot.download_file(file.file_path)
        photo_bytes = photo_buffer.read()
        base64photo = base64.b64encode(photo_bytes).decode("utf-8")
        encoded_photos.append(base64photo)
    place = Place()
    place.NameOfPlace = data.get("title")
    place.Description = data.get("discription")
    place.Address = data.get("adress")
    place.Photo1 = encoded_photos[0]
    place.Photo2 = encoded_photos[1]
    place.Photo3 = encoded_photos[2]
    place.Photo4 = encoded_photos[3]
    place.Photo5 = encoded_photos[4]
    async with aiohttp.ClientSession() as session:
        result = await add_custom_place(place, session)
    if result:
        await message.answer("Place added")
        # send_main_menu(message)
    else:
        await message.answer("We got error")
        # send_main_menu(message)
