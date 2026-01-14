import asyncio
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tapo import ApiClient
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)

from src.db.models import Status
from src.logger.main import logger
from src.utils import get_database_url, _require_env


def _is_retryable_exception(exc: Exception) -> bool:
    """Check if exception is retryable (transient network/API errors)."""
    # Retry on exceptions with "timeout" or "connection" in their name/message
    exc_name = type(exc).__name__.lower()
    exc_msg = str(exc).lower()
    if "TimedOut" in exc_name or "TimedOut" in exc_msg:
        return True
    return False


class DeviceTimeoutError(Exception):
    pass


def raise_custom_timeout(_: RetryCallState):
    raise DeviceTimeoutError()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),  # retry on ANY exception
    reraise=False,  # allow custom error
    retry_error_callback=raise_custom_timeout,
)
async def is_device_on(client: ApiClient, device_ip: str) -> bool:
    device = await asyncio.wait_for(client.p100(device_ip), 5)
    info = await asyncio.wait_for(device.get_device_info(), 5)
    return info.device_on


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


async def poll_once(session_factory: async_sessionmaker[AsyncSession], client: ApiClient, device_ip: str) -> None:
    # Add timeout to prevent hanging indefinitely (30s should be enough for retries)
    try:
        value = await is_device_on(client, device_ip)
    except DeviceTimeoutError:
        # Device is offline / tapo library behavior
        value = False
    except asyncio.TimeoutError:
        logger.error("Device status check timed out after 30s")
        raise

    async with session_factory() as session:
        changed = await record_event_if_changed(session, value)
        if changed:
            if value:
                from_v = "offline"
                to_v = "online"
            else:
                from_v = "online"
                to_v = "offline"
            logger.info(f"Device status changed: {from_v} -> {to_v}")


async def run_polling_loop() -> None:
    interval_s = float(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    tapo_email = _require_env("TAPO_EMAIL")
    tapo_password = _require_env("TAPO_PASSWORD")
    tapo_device_ip = _require_env("TAPO_DEVICE_IP")

    engine = create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    tapo_client = ApiClient(tapo_email, tapo_password)

    logger.info(f"Started polling every {interval_s:.1f}s")
    try:
        while True:
            try:
                await poll_once(session_factory, tapo_client, tapo_device_ip)
            except Exception as exc:
                # Keep the loop alive; transient network/Tapo failures shouldn't kill the scheduler.
                logger.error(f"Poll error: {exc!r}")
            await asyncio.sleep(interval_s)
    finally:
        await engine.dispose()


def start_scheduler() -> None:
    asyncio.run(run_polling_loop())
