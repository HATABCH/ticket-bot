# /Users/mac/projects/ticket_bot/app/handlers/client.py
import contextlib
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from app.database import crud
from app.database.database import get_session
from app.database.models import TicketStatus
from app.keyboards import client_kb, admin_kb
from app.config import settings
from app.services.notifications import notify_admins, notify_admins_new_message

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    async with get_session() as session:
        await crud.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        await message.answer(
            f"Здравствуйте, {message.from_user.full_name}!\n\n"
            "Это бот поддержки VPN. Чем могу помочь?",
            reply_markup=client_kb.get_main_menu(),
        )


@router.message(F.text == "Создать тикет")
async def create_ticket_handler(message: Message):
    async with get_session() as session:
        new_ticket = await crud.create_ticket(session, message.from_user.id)
        await crud.set_active_ticket(session, message.from_user.id, new_ticket.id)

        await message.answer(
            f"Тикет #{new_ticket.id} создан и установлен как активный. "
            "Все последующие сообщения будут направлены в этот тикет.",
            reply_markup=client_kb.get_active_ticket_menu(new_ticket.id),
        )

        # Уведомление админам
        await notify_admins(
            message.bot,
            f"Новый тикет #{new_ticket.id} от пользователя @{message.from_user.username} ({message.from_user.id})"
        )


@router.message(F.text == "Мои тикеты")
async def my_tickets_handler(message: Message):
    async with get_session() as session:
        tickets = await crud.get_user_tickets(session, message.from_user.id)
        if not tickets:
            await message.answer("У вас пока нет созданных тикетов.")
            return

        await message.answer(
            "Ваши тикеты:", reply_markup=await client_kb.get_user_tickets_kb(tickets)
        )


@router.message(F.text.startswith("Активный тикет"))
async def active_ticket_menu_handler(message: Message):
    async with get_session() as session:
        active_ticket_id = await crud.get_active_ticket_id(
            session, message.from_user.id
        )
        if not active_ticket_id:
            await message.answer(
                "У вас нет активного тикета. Создайте новый или выберите из списка существующих."
            )
            return

        await message.answer(
            f"Текущий активный тикет: #{active_ticket_id}",
            reply_markup=client_kb.get_active_ticket_menu(active_ticket_id),
        )


@router.callback_query(client_kb.TicketCallback.filter(F.action == "view"))
async def view_ticket_callback(
    query: CallbackQuery, callback_data: client_kb.TicketCallback
):
    async with get_session() as session:
        ticket_id = callback_data.ticket_id
        messages = await crud.get_ticket_messages(session, ticket_id)

        if not messages:
            await query.answer("В этом тикете пока нет сообщений.", show_alert=True)
            return

        history = f"<b>История сообщений по тикету #{ticket_id}</b>\n\n"
        for msg in messages:
            sender = "Вы" if msg.sender_id == query.from_user.id else "Поддержка"
            time = msg.created_at.strftime("%Y-%m-%d %H:%M")
            history += f"<u>{sender} ({time}):</u>\n"
            if msg.message_type == "text":
                history += f"{msg.text}\n\n"
            else:
                history += f"<i>[{msg.message_type.capitalize()}]</i>\n\n"

        # Отправляем историю в нескольких сообщениях, если она слишком длинная
        for i in range(0, len(history), 4096):
            await query.message.answer(history[i : i + 4096])

    await query.answer()


@router.callback_query(client_kb.TicketCallback.filter(F.action == "set_active"))
async def set_active_ticket_callback(
    query: CallbackQuery, callback_data: client_kb.TicketCallback
):
    async with get_session() as session:
        ticket_id = callback_data.ticket_id
        await crud.set_active_ticket(session, query.from_user.id, ticket_id)
        await query.message.edit_text(f"Активный тикет изменен на #{ticket_id}.")
        await query.answer(f"Тикет #{ticket_id} теперь активен.", show_alert=True)


@router.callback_query(client_kb.TicketCallback.filter(F.action == "close"))
async def close_ticket_callback(
    query: CallbackQuery, callback_data: client_kb.TicketCallback
):
    async with get_session() as session:
        ticket_id = callback_data.ticket_id
        await crud.update_ticket_status(session, ticket_id, TicketStatus.CLOSED)
        await query.message.edit_text(f"Тикет #{ticket_id} был закрыт.")
        await query.answer("Тикет закрыт.", show_alert=True)

        # Уведомление админам
        await notify_admins(
            query.bot,
            f"Пользователь @{query.from_user.username} закрыл тикет #{ticket_id}"
        )


@router.callback_query(client_kb.TicketCallback.filter(F.action == "reopen"))
async def reopen_ticket_callback(
    query: CallbackQuery, callback_data: client_kb.TicketCallback
):
    async with get_session() as session:
        ticket_id = callback_data.ticket_id
        # Клиент переоткрывает, значит ждем ответа админа
        await crud.update_ticket_status(session, ticket_id, TicketStatus.OPEN)
        await crud.set_active_ticket(session, query.from_user.id, ticket_id)
        await query.message.edit_text(
            f"Тикет #{ticket_id} был переоткрыт и установлен как активный."
        )
        await query.answer("Тикет переоткрыт.", show_alert=True)

        # Уведомление админам
        await notify_admins(
            query.bot,
            f"Пользователь @{query.from_user.username} переоткрыл тикет #{ticket_id}"
        )


@router.message(F.text == "Срок подписки")
async def subscription_status_handler(message: Message):
    async with get_session() as session:
        subscription = await crud.get_user_subscription(session, message.from_user.id)
        if not subscription:
            await message.answer(
                "Информация о вашей подписке не найдена. Обратитесь в поддержку."
            )
            return

        end_date = subscription.end_date
        days_left = (end_date.date() - datetime.utcnow().date()).days

        response = (
            f"Ваша подписка активна до: {end_date.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left if days_left >= 0 else 0}"
        )

        await message.answer(response)


@router.message(F.content_type.in_(("text", "photo", "video", "document")))
async def handle_message_in_ticket(message: Message, bot: Bot):
    # Игнорируем команды и кнопки главного меню
    if (
        message.text in ["Создать тикет", "Мои тикеты", "Срок подписки"]
        or (message.text and message.text.startswith("/"))
    ):
        return
    async with get_session() as session:
        active_ticket_id = await crud.get_active_ticket_id(
            session, message.from_user.id
        )
        if not active_ticket_id:
            await message.answer(
                "У вас нет активного тикета. "
                "Чтобы отправить сообщение, сначала создайте тикет или выберите существующий.",
                reply_markup=client_kb.get_main_menu(),
            )
            return

        ticket = await crud.get_ticket_by_id(session, active_ticket_id)
        if ticket.status == TicketStatus.CLOSED:
            user_tickets = await crud.get_user_tickets(session, message.from_user.id)
            await message.answer(
                "Этот тикет закрыт. Вы не можете отправлять в него сообщения. "
                "Переоткройте его или создайте новый.",
                reply_markup=await client_kb.get_user_tickets_kb(user_tickets),
            )
            return

        content_type = message.content_type.value
        text = message.text or message.caption
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.document:
            file_id = message.document.file_id

        await crud.add_message_to_ticket(
            session,
            active_ticket_id,
            message.from_user.id,
            content_type,
            text,
            file_id,
        )

        # Меняем статус, так как клиент ответил
        await crud.update_ticket_status(session, active_ticket_id, TicketStatus.ANSWERED)

        await message.answer("Ваше сообщение отправлено в поддержку.")

        # Уведомление для админов
        await notify_admins_new_message(message.bot, message, active_ticket_id)
