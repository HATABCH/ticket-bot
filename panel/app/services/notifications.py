# /Users/mac/projects/ticket_bot/app/services/notifications.py
import logging
import contextlib
from datetime import datetime
from aiogram import Bot
from app.database import crud
from app.database.database import AsyncSessionFactory

logger = logging.getLogger(__name__)

async def check_sla(bot: Bot, sla_hours: int):
    """Проверяет тикеты на нарушение SLA и отправляет уведомления."""
    logger.info("Running SLA check...")
    async with AsyncSessionFactory() as session:
        try:
            tickets_to_notify = await crud.find_tickets_for_sla_check(session, sla_hours)
            if not tickets_to_notify:
                logger.info("SLA check complete. No violations found.")
                return

            for ticket in tickets_to_notify:
                user = await crud.get_user_by_id(session, ticket.owner_id)
                for admin_id in bot.settings.admin_ids:
                    with contextlib.suppress(Exception):
                        await bot.send_message(
                            admin_id,
                            f"⚠️ <b>SLA НАРУШЕНИЕ</b> ⚠️\n\n"
                            f"Тикет #{ticket.id} от пользователя @{user.username} ({user.telegram_id}) "
                            f"ожидает ответа более {sla_hours} часов."
                        )
            logger.info(f"SLA check complete. Found {len(tickets_to_notify)} violations.")
        except Exception as e:
            logger.error(f"Error during SLA check: {e}")


async def check_subscriptions(bot: Bot):
    """Проверяет истекающие подписки и уведомляет пользователей."""
    logger.info("Running subscription check...")
    async with AsyncSessionFactory() as session:
        try:
            subscriptions_to_notify = await crud.find_subscriptions_for_notification(session)
            if not subscriptions_to_notify:
                logger.info("Subscription check complete. No expiring subscriptions found.")
                return

            today = datetime.utcnow().date()
            for sub in subscriptions_to_notify:
                end_date = sub.end_date.date()
                days_left = (end_date - today).days
                
                message = ""
                if days_left == 1:
                    message = "👋 Напоминаем, что ваша VPN-подписка истекает завтра."
                elif days_left == 0:
                    message = "❗️ Ваша VPN-подписка истекает сегодня. Для продления обратитесь в поддержку."

                if message:
                    with contextlib.suppress(Exception):
                        await bot.send_message(sub.user_id, message)
            
            logger.info(f"Subscription check complete. Notified {len(subscriptions_to_notify)} users.")
        except Exception as e:
            logger.error(f"Error during subscription check: {e}")
