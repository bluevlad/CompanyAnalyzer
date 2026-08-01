from app.core.config import get_settings, Settings
from app.database.connection import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


async def get_database(db: AsyncSession = Depends(get_db)):
    return db


def get_config() -> Settings:
    return get_settings()
