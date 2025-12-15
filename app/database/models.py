# /Users/mac/projects/ticket_bot/app/database/models.py
import enum
from sqlalchemy import (Column, Integer, String, DateTime, Enum, ForeignKey, BigInteger, Text)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class TicketStatus(enum.Enum):
    OPEN = "open"
    PENDING = "pending" # Ждет ответа клиента
    ANSWERED = "answered" # Ждет ответа админа
    CLOSED = "closed"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String)
    active_ticket_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tickets = relationship("Ticket", back_populates="owner")
    subscription = relationship("Subscription", uselist=False, back_populates="user")

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(BigInteger, ForeignKey('users.telegram_id'))
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_message_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    owner = relationship("User", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")

class TicketMessage(Base):
    __tablename__ = 'ticket_messages'
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    sender_id = Column(BigInteger)
    message_type = Column(String) # 'text', 'photo', 'video', 'document'
    text = Column(Text, nullable=True)
    file_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), unique=True)
    end_date = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="subscription")
