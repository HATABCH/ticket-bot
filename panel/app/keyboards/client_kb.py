# /Users/mac/projects/ticket_bot/app/keyboards/client_kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List
from app.database.models import Ticket, TicketStatus

class TicketCallback(CallbackData, prefix="ticket"):
    action: str
    ticket_id: int

def get_main_menu() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру главного меню клиента."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать тикет"), KeyboardButton(text="Мои тикеты")],
            [KeyboardButton(text="Активный тикет"), KeyboardButton(text="Срок подписки")],
        ],
        resize_keyboard=True
    )

async def get_user_tickets_kb(tickets: List[Ticket]) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру со списком тикетов пользователя."""
    buttons = []
    for ticket in tickets:
        status_emoji = {
            TicketStatus.OPEN: "🟢",
            TicketStatus.ANSWERED: "🟡",
            TicketStatus.PENDING: "🔵",
            TicketStatus.CLOSED: "🔴",
        }.get(ticket.status, "⚪️")
        
        text = f"{status_emoji} Тикет #{ticket.id} - {ticket.status.name}"
        
        # Для закрытых тикетов даем опцию переоткрыть, для остальных - сделать активным
        if ticket.status == TicketStatus.CLOSED:
            action_button = InlineKeyboardButton(
                text="Переоткрыть",
                callback_data=TicketCallback(action="reopen", ticket_id=ticket.id).pack()
            )
        else:
            action_button = InlineKeyboardButton(
                text="Сделать активным",
                callback_data=TicketCallback(action="set_active", ticket_id=ticket.id).pack()
            )

        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=TicketCallback(action="view", ticket_id=ticket.id).pack()
            ),
            action_button
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_active_ticket_menu(ticket_id: int) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для управления активным тикетом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Посмотреть историю",
                    callback_data=TicketCallback(action="view", ticket_id=ticket_id).pack()
                ),
                InlineKeyboardButton(
                    text="Закрыть тикет",
                    callback_data=TicketCallback(action="close", ticket_id=ticket_id).pack()
                )
            ]
        ]
    )
