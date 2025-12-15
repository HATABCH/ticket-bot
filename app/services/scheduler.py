# /Users/mac/projects/ticket_bot/app/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from app.config import settings
from . import notifications

async def setup_scheduler(bot: Bot):
    """Настраивает и возвращает экземпляр планировщика."""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Добавляем задачу для проверки SLA
    scheduler.add_job(
        notifications.check_sla, 
        'interval', 
        minutes=30, 
        args=(bot, settings.sla_hours)
    )
    
    # Добавляем задачу для проверки подписок (например, раз в день в 9 утра)
    scheduler.add_job(
        notifications.check_subscriptions,
        'cron',
        hour=9,
        minute=0,
        args=(bot,)
    )
    
    return scheduler
