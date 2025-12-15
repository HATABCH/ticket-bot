# /Users/mac/projects/ticket_bot/app/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Settings
from app.database.database import init_db, get_session
from app.handlers import client, admin
from app.services.scheduler import setup_scheduler

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота."""
    logger.info("Starting bot...")

    # Загрузка конфигурации
    settings = Settings()

    # Инициализация базы данных
    await init_db()
    logger.info("Database initialized.")

    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot_token, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрация роутеров
    dp.include_router(client.router)
    dp.include_router(admin.router)
    logger.info("Routers included.")

    # Настройка и запуск фоновых задач
    scheduler = await setup_scheduler(bot)
    try:
        scheduler.start()
        logger.info("Scheduler started.")

        # Запуск поллинга
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
        await bot.session.close()
        logger.info("Bot session closed.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
