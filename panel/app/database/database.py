# /Users/mac/projects/ticket_bot/app/database/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from .models import Base
import logging

logger = logging.getLogger(__name__)

# Создание асинхронного движка
engine = create_async_engine(settings.db_url, echo=False)

# Создание фабрики сессий
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with engine.begin() as conn:
        try:
            # await conn.run_sync(Base.metadata.drop_all) # Для отладки, удаляет все таблицы
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

async def get_session() -> AsyncSession:
    """Зависимость для получения сессии базы данных."""
    session = AsyncSessionFactory()
    try:
        yield session
    finally:
        await session.close()
