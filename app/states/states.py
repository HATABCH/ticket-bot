# /Users/mac/projects/ticket_bot/app/states/states.py
from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    reply_to_ticket = State()
    write_to_user_id = State()
    write_to_user_message = State()

class ManageSubscription(StatesGroup):
    get_user_id = State()
    get_end_date = State()
