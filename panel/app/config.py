# /Users/mac/projects/ticket_bot/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # Telegram Bot Token
        self.bot_token: str = os.getenv("BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is not set in the environment variables.")

        # Admin Telegram IDs
        admin_ids_str = os.getenv("ADMIN_IDS")
        if not admin_ids_str:
            raise ValueError("ADMIN_IDS is not set in the environment variables.")
        self.admin_ids: list[int] = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',')]

        # SLA Timer in hours
        self.sla_hours: int = int(os.getenv("SLA_HOURS", 12))

        # Database URL
        self.db_url: str = "sqlite+aiosqlite:///app/database/data/database.db"

# Instantiate settings to be imported in other modules
settings = Settings()
