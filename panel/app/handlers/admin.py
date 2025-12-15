# /Users/mac/projects/ticket_bot/app/handlers/admin.py
import contextlib
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import crud
from app.database.models import TicketStatus
from app.keyboards import admin_kb
from app.config import settings
from app.states.states import AdminState

router = Router()
router.message.filter(F.from_user.id.in_(settings.admin_ids))
router.callback_query.filter(F.from_user.id.in_(settings.admin_ids))

async def get_db_session(message: Message) -> AsyncSession:
    async for session in crud.get_session():
        return session

@router.message(Command("admin"))
async def admin_menu_handler(message: Message):
    await message.answer("Админ-панель", reply_markup=admin_kb.get_admin_main_menu())

@router.message(F.text == "Открытые тикеты")
async def open_tickets_handler(message: Message, session: AsyncSession = None):
    if not session:
        session = await get_db_session(message)
    
    open_tickets = await crud.get_tickets_by_status(session, TicketStatus.OPEN)
    answered_tickets = await crud.get_tickets_by_status(session, TicketStatus.ANSWERED)
    
    tickets = open_tickets + answered_tickets
    
    if not tickets:
        await message.answer("Нет открытых тикетов.")
        return
        
    await message.answer("Открытые тикеты:", reply_markup=await admin_kb.get_tickets_list_kb(tickets, "open"))

@router.message(F.text == "Закрытые тикеты")
async def closed_tickets_handler(message: Message, session: AsyncSession = None):
    if not session:
        session = await get_db_session(message)
        
    tickets = await crud.get_tickets_by_status(session, TicketStatus.CLOSED)
    
    if not tickets:
        await message.answer("Нет закрытых тикетов.")
        return
        
    await message.answer("Закрытые тикеты:", reply_markup=await admin_kb.get_tickets_list_kb(tickets, "closed"))

@router.callback_query(admin_kb.AdminTicketCallback.filter())
async def handle_admin_ticket_action(query: CallbackQuery, callback_data: admin_kb.AdminTicketCallback, state: FSMContext, session: AsyncSession = None):
    if not session:
        session = await get_db_session(query.message)
        
    ticket_id = callback_data.ticket_id
    action = callback_data.action
    user_id = callback_data.user_id

    if action == "view_ticket":
        messages = await crud.get_ticket_messages(session, ticket_id)
        ticket = await crud.get_ticket_by_id(session, ticket_id)
        user = await crud.get_user_by_id(session, ticket.owner_id)
        
        history = f"<b>История сообщений по тикету #{ticket_id}</b>\nПользователь: @{user.username} ({user.telegram_id})\nСтатус: {ticket.status.value}\n\n"
        for msg in messages:
            sender = "Клиент" if msg.sender_id == user.telegram_id else "Поддержка"
            time = msg.created_at.strftime('%Y-%m-%d %H:%M')
            history += f"<u>{sender} ({time}):</u>\n"
            if msg.message_type == 'text':
                history += f"{msg.text}\n\n"
            else:
                history += f"<i>[{msg.message_type.capitalize()}]</i>\n\n"

        for i in range(0, len(history), 4096):
            await query.message.answer(history[i:i+4096], reply_markup=admin_kb.get_ticket_actions_kb(ticket_id, user.telegram_id))
    
    elif action == "reply_to_ticket":
        await state.set_state(AdminState.reply_to_ticket)
        await state.update_data(ticket_id=ticket_id, user_id=user_id)
        await query.message.answer(f"Введите ответ для тикета #{ticket_id}:")

    elif action == "close_ticket":
        await crud.update_ticket_status(session, ticket_id, TicketStatus.CLOSED)
        await query.message.edit_text(f"Тикет #{ticket_id} закрыт.")
        with contextlib.suppress(Exception):
            await query.bot.send_message(user_id, f"Ваш тикет #{ticket_id} был закрыт администратором.")
    
    elif action == "reopen_ticket":
        await crud.update_ticket_status(session, ticket_id, TicketStatus.PENDING)
        await query.message.edit_text(f"Тикет #{ticket_id} переоткрыт.")
        with contextlib.suppress(Exception):
            await query.bot.send_message(user_id, f"Ваш тикет #{ticket_id} был переоткрыт администратором.")

    await query.answer()

@router.message(AdminState.reply_to_ticket)
async def process_reply(message: Message, state: FSMContext, bot: Bot, session: AsyncSession = None):
    if not session:
        session = await get_db_session(message)

    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    user_id = data.get("user_id")

    content_type = message.content_type.value
    text = message.text or message.caption
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id

    await crud.add_message_to_ticket(session, ticket_id, message.from_user.id, content_type, text, file_id)
    # Админ ответил, значит ждем ответа клиента
    await crud.update_ticket_status(session, ticket_id, TicketStatus.PENDING)

    await message.answer(f"Ваш ответ в тикет #{ticket_id} отправлен.")
    
    # Уведомляем клиента
    with contextlib.suppress(Exception):
        await bot.send_message(user_id, f"Поступил ответ от поддержки в тикете #{ticket_id}")
        await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)

    await state.clear()

@router.message(F.text == "Написать пользователю")
async def write_to_user_start(message: Message, state: FSMContext):
    await state.set_state(AdminState.write_to_user_id)
    await message.answer("Введите Telegram ID пользователя, которому хотите написать:")

@router.message(AdminState.write_to_user_id)
async def get_user_id_for_message(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте снова.")
        return

    await state.update_data(target_user_id=int(message.text))
    await state.set_state(AdminState.write_to_user_message)
    await message.answer("Теперь введите сообщение для этого пользователя:")

@router.message(AdminState.write_to_user_message)
async def send_direct_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get("target_user_id")
    
    try:
        await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("Сообщение успешно отправлено.")
    except Exception as e:
        await message.answer(f"Не удалось отправить сообщение пользователю {user_id}. Ошибка: {e}")
    
    await state.clear()
    
@router.message(F.text == "Истекающие подписки")
async def expiring_subscriptions_handler(message: Message, session: AsyncSession = None):
    if not session:
        session = await get_db_session(message)
    
    subscriptions = await crud.get_expiring_subscriptions(session, days=7) # Например, за 7 дней
    if not subscriptions:
        await message.answer("Нет подписок, истекающих в ближайшее время.")
        return

    response = "<b>Истекающие подписки (ближайшие 7 дней):</b>\n\n"
    for sub in sorted(subscriptions, key=lambda s: s.end_date):
        user = await crud.get_user_by_id(session, sub.user_id)
        response += f"Пользователь: @{user.username} ({user.telegram_id})\n"
        response += f"Дата окончания: {sub.end_date.strftime('%d.%m.%Y')}\n\n"
        
    await message.answer(response)
