import asyncio
import os
from typing import Optional
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models import Status, Heartbeat
from src.logger.main import logger
from src.utils import get_database_url

HEARTBEAT_ID = 1
LAST_SEEN_TIMESTAMP = None
WAIT_TILL_MAKE_DECISION = 5


async def get_heartbeat(session: AsyncSession) -> Heartbeat | None:
    result = await session.execute(select(Heartbeat).where(Heartbeat.id == HEARTBEAT_ID).limit(1))
    return result.scalar_one_or_none()


async def get_last_event_value(session: AsyncSession) -> Optional[bool]:
    result = await session.execute(select(Status.value).order_by(Status.date_created.desc()).limit(1))
    return result.scalar_one_or_none()


async def record_event_if_changed(session: AsyncSession, value: bool) -> bool:
    last_value = await get_last_event_value(session)

    if last_value is not None and last_value == value:
        return False

    session.add(Status(value=value))
    await session.commit()
    return True


def detect_power_value(current_dt: datetime, heartbeat_dt: datetime, interval: int) -> bool:
    # Business logic desc:
    # If time diff became too large between current datetime and datetime from DB,
    # it means that power outage happen and client that performs heartbeat is dead -> interpret as POWER_OFF.
    # If the diff is within acceptable limits -> interpret as POWER_ON
    diff = current_dt - heartbeat_dt
    compare = int(interval) * WAIT_TILL_MAKE_DECISION
    return diff.seconds <= compare


async def poll_once(session_factory: async_sessionmaker[AsyncSession], interval: int) -> None:
    global LAST_SEEN_TIMESTAMP

    async with session_factory() as session:
        heartbeat = await get_heartbeat(session)
        if not heartbeat:
            logger.warning("Heartbeat not found")
            return

        LAST_SEEN_TIMESTAMP = datetime.now(UTC)
        power_value = detect_power_value(
            current_dt=LAST_SEEN_TIMESTAMP, heartbeat_dt=heartbeat.timestamp, interval=interval
        )
        changed = await record_event_if_changed(session, power_value)

        if changed:
            from_v = "offline" if power_value else "online"
            to_v = "online" if power_value else "offline"
            logger.info(f"Device status changed: {from_v} -> {to_v}")


async def run_polling_loop() -> None:
    interval_s = float(os.getenv("LISTEN_HEARTBEAT_INTERVAL_SECONDS", "10"))

    engine = create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    logger.info(f"Started polling every {interval_s:.1f}s")
    try:
        while True:
            try:
                await poll_once(session_factory, int(interval_s))
            except Exception as exc:
                # Keep the loop alive
                logger.error(f"Poll error: {exc!r}")
            await asyncio.sleep(interval_s)
    finally:
        await engine.dispose()


def start_scheduler() -> None:
    asyncio.run(run_polling_loop())
