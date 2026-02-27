from aiogram.fsm.state import StatesGroup, State

class AddPlace(StatesGroup):
    wait_for_title = State()
    wait_for_discription = State()
    wait_for_shor_adress = State()
    wait_for_foto = State()
    wait_for_confirm = State()
