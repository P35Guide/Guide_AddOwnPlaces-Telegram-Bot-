@router.message(BotState.waiting_for_category)
async def add_custom_category_handler(message: Message, state: FSMContext):
    user_text = (message.text or "").strip()

    if len(user_text) < 3:
        await message.answer("⚠️ Занадто коротка назва. Спробуйте ще раз або оберіть кнопку.")
        return

    settings_service.add_included_type(message.from_user.id, user_text)
    await message.answer(f"✅ Прийнято! Шукаю нестандартну категорію: **{user_text}**")
    await state.clear()
    await send_main_menu(message)