# /Users/mac/projects/ticket_bot/app/database/crud.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from app.database.models import User, Ticket, TicketMessage, Subscription, TicketStatus
from typing import List, Optional

# User CRUD
async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str) -> User:
    result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def get_user_by_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).filter(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def set_active_ticket(session: AsyncSession, telegram_id: int, ticket_id: int):
    await session.execute(update(User).where(User.telegram_id == telegram_id).values(active_ticket_id=ticket_id))
    await session.commit()

async def get_active_ticket_id(session: AsyncSession, telegram_id: int) -> Optional[int]:
    result = await session.execute(select(User.active_ticket_id).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

# Ticket CRUD
async def create_ticket(session: AsyncSession, telegram_id: int) -> Ticket:
    new_ticket = Ticket(owner_id=telegram_id, status=TicketStatus.OPEN)
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket

async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Optional[Ticket]:
    result = await session.execute(select(Ticket).filter(Ticket.id == ticket_id))
    return result.scalar_one_or_none()

async def get_user_tickets(session: AsyncSession, telegram_id: int) -> List[Ticket]:
    result = await session.execute(
        select(Ticket).filter(Ticket.owner_id == telegram_id).order_by(Ticket.last_message_at.desc())
    )
    return result.scalars().all()

async def get_tickets_by_status(session: AsyncSession, status: TicketStatus) -> List[Ticket]:
    result = await session.execute(
        select(Ticket).filter(Ticket.status == status).order_by(Ticket.last_message_at.asc())
    )
    return result.scalars().all()

async def update_ticket_status(session: AsyncSession, ticket_id: int, status: TicketStatus):
    await session.execute(update(Ticket).where(Ticket.id == ticket_id).values(status=status, last_message_at=datetime.utcnow()))
    await session.commit()

# TicketMessage CRUD
async def add_message_to_ticket(session: AsyncSession, ticket_id: int, sender_id: int, message_type: str, text: str = None, file_id: str = None):
    new_message = TicketMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        message_type=message_type,
        text=text,
        file_id=file_id
    )
    session.add(new_message)
    # Update ticket's last message time
    await session.execute(update(Ticket).where(Ticket.id == ticket_id).values(last_message_at=datetime.utcnow()))
    await session.commit()

async def get_ticket_messages(session: AsyncSession, ticket_id: int) -> List[TicketMessage]:
    result = await session.execute(
        select(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at.asc())
    )
    return result.scalars().all()

# Subscription CRUD
async def get_user_subscription(session: AsyncSession, telegram_id: int) -> Optional[Subscription]:
    result = await session.execute(select(Subscription).filter(Subscription.user_id == telegram_id))
    return result.scalar_one_or_none()

async def get_expiring_subscriptions(session: AsyncSession, days: int) -> List[Subscription]:
    target_date = datetime.utcnow().date() + timedelta(days=days)
    result = await session.execute(
        select(Subscription).filter(func.date(Subscription.end_date) <= target_date)
    )
    return result.scalars().all()
    
async def find_tickets_for_sla_check(session: AsyncSession, sla_hours: int) -> List[Ticket]:
    time_threshold = datetime.utcnow() - timedelta(hours=sla_hours)
    result = await session.execute(
        select(Ticket).where(
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.ANSWERED]),
            Ticket.last_message_at < time_threshold
        )
    )
    return result.scalars().all()

async def find_subscriptions_for_notification(session: AsyncSession) -> List[Subscription]:
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    result = await session.execute(
        select(Subscription).where(
            (func.date(Subscription.end_date) == today) | (func.date(Subscription.end_date) == tomorrow)
        )
    )
    return result.scalars().all()
