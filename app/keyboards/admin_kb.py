# /Users/mac/projects/ticket_bot/app/keyboards/admin_kb.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from typing import List
from app.database.models import Ticket, TicketStatus

class AdminTicketCallback(CallbackData, prefix="admin_ticket"):
    action: str
    ticket_id: int
    user_id: int # Добавляем user_id для прямого ответа

class ManageSubscriptionCallback(CallbackData, prefix="manage_sub"):
    action: str
    user_id: int
    months: int = 0

def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру главного меню администратора."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открытые тикеты"), KeyboardButton(text="Закрытые тикеты")],
            [KeyboardButton(text="Истекающие подписки"), KeyboardButton(text="Написать пользователю")],
            [KeyboardButton(text="Управление подпиской")]
        ],
        resize_keyboard=True
    )

async def get_tickets_list_kb(tickets: List[Ticket], ticket_type: str) -> InlineKeyboardMarkup:
    """
    Возвращает инлайн-клавиатуру со списком тикетов для админа.
    ticket_type: 'open' или 'closed'
    """
    buttons = []
    for ticket in tickets:
        status_emoji = {
            TicketStatus.OPEN: "🟢",     # Новый, не отвеченный
            TicketStatus.ANSWERED: "🟡", # Клиент ответил, ждет админа
            TicketStatus.PENDING: "🔵",  # Админ ответил, ждет клиента
            TicketStatus.CLOSED: "🔴",   # Закрыт
        }.get(ticket.status, "⚪️")
        
        text = f"{status_emoji} Тикет #{ticket.id} от {ticket.owner_id}"
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=AdminTicketCallback(
                    action="view_ticket", 
                    ticket_id=ticket.id, 
                    user_id=ticket.owner_id
                ).pack()
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ticket_actions_kb(ticket_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру с действиями для конкретного тикета."""
    buttons = [
        [
            InlineKeyboardButton(
                text="Ответить",
                callback_data=AdminTicketCallback(action="reply_to_ticket", ticket_id=ticket_id, user_id=user_id).pack()
            ),
             InlineKeyboardButton(
                text="Посмотреть историю",
                callback_data=AdminTicketCallback(action="view_ticket", ticket_id=ticket_id, user_id=user_id).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="Закрыть тикет",
                callback_data=AdminTicketCallback(action="close_ticket", ticket_id=ticket_id, user_id=user_id).pack()
            ),
            InlineKeyboardButton(
                text="Переоткрыть тикет",
                callback_data=AdminTicketCallback(action="reopen_ticket", ticket_id=ticket_id, user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_subscription_management_kb(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для управления подпиской."""
    buttons = [
        [
            InlineKeyboardButton(
                text="Продлить на 1 месяц",
                callback_data=ManageSubscriptionCallback(action="renew", user_id=user_id, months=1).pack()
            ),
            InlineKeyboardButton(
                text="Продлить на 3 месяца",
                callback_data=ManageSubscriptionCallback(action="renew", user_id=user_id, months=3).pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="Ввести дату вручную",
                callback_data=ManageSubscriptionCallback(action="manual", user_id=user_id).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_extend_subscription_kb(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает инлайн-клавиатуру для продления подписки."""
    buttons = [
        [
            InlineKeyboardButton(
                text="Продлить на 1 месяц",
                callback_data=ManageSubscriptionCallback(action="renew", user_id=user_id, months=1).pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
