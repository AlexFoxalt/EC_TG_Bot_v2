import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from src.db.models import Base
from src.utils import get_database_url
from src.logger.main import logger


async def _refresh_db():
    engine = create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def refresh_db() -> None:
    asyncio.run(_refresh_db())
    logger.info("Refreshed successfully!")
