import asyncio
from datetime import datetime, timedelta
import re

from aiolimiter import AsyncLimiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, Application
from telegram.error import TimedOut, NetworkError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, before_sleep_log

from src.bot.constants import (
    NIGHT_START_HOUR,
    NIGHT_END_HOUR,
    KYIV_TZ,
    GEN_WORKTIME_SCHEDULE_WEEKDAY,
    GEN_WORKTIME_SCHEDULE_WEEKEND,
)
from src.bot.lang_pack.base import BaseLangPack
from src.db.models import User
from src.logger.main import logger


async def cleanup_registration_context(context: ContextTypes.DEFAULT_TYPE, user_identity: str) -> None:
    """Clean up registration/reconfiguration context and log completion."""
    is_reconfiguration = context.user_data.get("is_reconfiguration", False)
    context.user_data.pop("registering_user_id", None)
    context.user_data.pop("is_reconfiguration", None)
    logger.bind(username=user_identity).info(
        f"{'Settings reconfiguration' if is_reconfiguration else 'Registration'} flow completed"
    )


def _is_retryable_telegram_exception(exc: Exception) -> bool:
    """Check if exception is retryable (transient network/API errors for Telegram)."""
    # Retry on network-related errors
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    # Retry on telegram library specific errors
    if isinstance(exc, (TimedOut, NetworkError)):
        return True

    # Check for Telegram-specific exceptions
    exc_name = type(exc).__name__.lower()
    exc_msg = str(exc).lower()

    # Retry on network/timeout related exceptions
    if "network" in exc_name or "network" in exc_msg:
        return True
    if "timeout" in exc_name or "timeout" in exc_msg:
        return True
    if "connection" in exc_name or "connection" in exc_msg:
        return True

    # Retry on rate limiting (429) - Telegram may rate limit
    if "retry" in exc_name or "rate" in exc_name or "429" in exc_msg:
        return True

    # Retry on server errors (5xx)
    if hasattr(exc, "status_code"):
        status_code = getattr(exc, "status_code", None)
        if status_code and status_code >= 500:
            return True

    # Retry on temporary Telegram API errors
    if hasattr(exc, "error_code"):
        # Some Telegram errors are temporary (like 500, 502, 503)
        error_code = getattr(exc, "error_code", None)
        if error_code in (500, 502, 503, 504):
            return True

    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception(_is_retryable_telegram_exception),
    reraise=True,  # Reraise after retries - we'll catch in outer function
    before_sleep=before_sleep_log(logger, "WARNING"),
)
async def send_message_with_retry(
    bot_app: Application,
    semaphore: asyncio.Semaphore,
    rate_limiter: AsyncLimiter,
    user_id: int,
    message_text: str,
    disable_sound: bool,
    markdown: bool = True,
) -> None:
    """Internal function to send message with retry logic.

    Retries up to 3 times on transient errors (network, timeouts, rate limits).
    Uses exponential backoff: 1s, 2s, 4s (max 5s).
    """
    if markdown:
        parse_mode = ParseMode.MARKDOWN_V2
    else:
        parse_mode = None
    async with semaphore:
        async with rate_limiter:
            await bot_app.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=parse_mode,
                disable_notification=disable_sound,
            )


def is_nighttime() -> bool:
    """Check if current time is nighttime (22:00 - 08:00 Kyiv time)."""
    now = datetime.now(KYIV_TZ)
    hour = now.hour
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def get_user_identity_from_update(update: Update) -> str:
    """Extract username from update for logging."""
    user = update.effective_user
    if user is None:
        return "Unknown(null)"
    username = user.username or "User"
    user_id = user.id
    return f"{username}({user_id})"


def get_user_identity_from_query(query) -> str:
    """Extract username from callback query for logging."""
    if query is None or query.from_user is None:
        return "Unknown(null)"
    user = query.from_user
    username = user.username or "User"
    user_id = user.id
    return f"{username}({user_id})"


def _get_gen_schedule_for_date(current_time: datetime) -> list[tuple[int, int, bool]]:
    is_weekend = current_time.weekday() >= 5
    return GEN_WORKTIME_SCHEDULE_WEEKEND if is_weekend else GEN_WORKTIME_SCHEDULE_WEEKDAY


def get_generator_schedule_status(current_time: datetime) -> bool:
    current_minutes = current_time.hour * 60 + current_time.minute
    schedule = _get_gen_schedule_for_date(current_time)

    for start_time, end_time, is_on in schedule:
        if start_time <= current_minutes < end_time:
            return is_on

    # Safety fallback (should never happen)
    return False


def get_generator_time_to_next_switch(current_time: datetime) -> timedelta:
    current_minutes = current_time.hour * 60 + current_time.minute
    schedule = _get_gen_schedule_for_date(current_time)

    for start_time, end_time, _ in schedule:
        if start_time <= current_minutes < end_time:
            minutes_left = end_time - current_minutes
            return timedelta(minutes=minutes_left)

    # Safety fallback (should never happen)
    return timedelta(0)


async def get_user_from_db(session_factory: async_sessionmaker, user_id: int) -> User | None:
    """Get user from database by ID."""
    if session_factory is None:
        return None
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


def get_completion_message(
    langpack: BaseLangPack,
    is_reconfiguration: bool,
    notifications_enabled: bool,
    night_sound_enabled: bool | None = None,
) -> str:
    """Get completion message based on flow type and settings."""
    if not notifications_enabled:
        return (
            langpack.MSG_NOTIFS_DISABLED
            if is_reconfiguration
            else f"{langpack.MSG_NOTIFS_DISABLED}\n\n{langpack.MSG_REGISTRATION_COMPLETED}"
        )

    if night_sound_enabled is not None:
        sound_status = langpack.WORD_ENABLED_LOWER if night_sound_enabled else langpack.WORD_DISABLED_LOWER
        emoji = "🔊" if night_sound_enabled else "🔇"
        return (
            f"{langpack.MSG_NOTIF_NIGHT_SOUND} {sound_status} {emoji}\n\n{langpack.MSG_SETTINGS_UPDATED}"
            if is_reconfiguration
            else f"{langpack.MSG_NOTIF_NIGHT_SOUND} {sound_status} {emoji}\n\n{langpack.MSG_REGISTRATION_COMPLETED}"
        )

    return ""


def build_button_pattern(attr: str, languages: list[BaseLangPack]) -> str:
    options = [re.escape(getattr(lang, attr)) for lang in languages]
    return f"^(?:{'|'.join(options)})$"
