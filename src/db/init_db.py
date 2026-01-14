import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from src.db.models import Base
from src.logger.main import logger
from src.utils import get_database_url


async def _init_db():
    engine = create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db():
    asyncio.run(_init_db())
    logger.info("Initiated successfully!")
