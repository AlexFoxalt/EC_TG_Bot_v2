import asyncio
import os
from collections import deque
from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from telegram import Update
from telegram.error import NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from src.bot.handlers.callback_query.night_sound import handle_night_sound_choice
from src.bot.handlers.callback_query.notifications import handle_notification_choice
from src.bot.handlers.command.msg_all import msg_all
from src.bot.handlers.command.start import start
from src.bot.handlers.message.gen_status import handle_gen_status
from src.bot.handlers.message.power_status import handle_power_status
from src.bot.handlers.message.report_error import handle_report_error
from src.bot.handlers.message.settings import handle_settings
from src.bot.jobs.power_notifications import check_and_send_notifications

from src.bot.lang_pack.container import LangContainer
from src.bot.utils import build_button_pattern
from src.logger.main import logger
from src.utils import _require_env, get_database_url

if TYPE_CHECKING:
    from telegram.ext import Application


async def handle_app_error(_: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, NetworkError) and "Bad Gateway" in str(error):
        logger.bind(username="system").warning("Telegram polling temporary error: Bad Gateway")
        return
    logger.bind(username="system").error(f"Unhandled bot error: {type(error).__name__}: {error}")


def start_bot() -> None:
    """Initialize and start the Telegram bot."""
    logger.info("Initializing Telegram bot...")

    # Create database session factory
    database_url = get_database_url()
    logger.info("Creating database engine connection (host from env)")
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Database session factory created successfully")

    app = ApplicationBuilder().token(_require_env("TELEGRAM_TOKEN")).build()
    logger.info("Telegram application builder initialized")

    rate_limit_per_sec = float(os.getenv("BOT_NOTIF_RATE_LIMIT_PER_SEC", "20"))
    max_concurrency = int(os.getenv("BOT_NOTIF_MAX_CONCURRENCY", "10"))
    if rate_limit_per_sec <= 0:
        rate_limit_per_sec = 1.0
    if max_concurrency <= 0:
        max_concurrency = 1

    logger.info(f"Notification rate limiting configured: {rate_limit_per_sec:.1f}/s, max_concurrency={max_concurrency}")

    languages = LangContainer()
    language_list = list(languages)
    logger.info(f"Langpack initialized. Available languages: {language_list}")

    button_rate_limit_per_sec = int(os.getenv("BOT_BUTTON_RATE_LIMIT_PER_SEC", "3"))
    if button_rate_limit_per_sec <= 0:
        button_rate_limit_per_sec = 1
    button_rate_limit_window_seconds = 1.0
    logger.info(
        "Button rate limiting configured: "
        f"{button_rate_limit_per_sec}/s per user, window={button_rate_limit_window_seconds:.1f}s"
    )

    # Shared state
    app.bot_data["app"]: Application = app
    app.bot_data["session_factory"]: async_sessionmaker[AsyncSession] = session_factory
    app.bot_data["rate_limiter"]: AsyncLimiter = AsyncLimiter(rate_limit_per_sec, time_period=1)
    app.bot_data["semaphore"]: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)
    app.bot_data["languages"]: LangContainer = languages
    app.bot_data["last_notified_status_id"]: int | None = None
    app.bot_data["button_rate_limit_per_sec"]: int = button_rate_limit_per_sec
    app.bot_data["button_rate_limit_window_seconds"]: float = button_rate_limit_window_seconds
    app.bot_data["button_rate_limit_buckets"]: dict[int, deque[float]] = {}

    # Add handlers
    app.add_error_handler(handle_app_error)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("msgAll", msg_all))
    app.add_handler(CallbackQueryHandler(handle_notification_choice, pattern="^notif_(yes|no)$"))
    app.add_handler(CallbackQueryHandler(handle_night_sound_choice, pattern="^night_sound_(yes|no)$"))

    # Language-specific commands (mainly from keyboard)
    app.add_handler(
        MessageHandler(
            filters.Regex(build_button_pattern("BTN_POWER_STATUS", language_list)),
            handle_power_status,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.Regex(build_button_pattern("BTN_GEN_STATUS", language_list)),
            handle_gen_status,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.Regex(build_button_pattern("BTN_SETTINGS", language_list)),
            handle_settings,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.Regex(build_button_pattern("BTN_REPORT_ERROR", language_list)),
            handle_report_error,
        )
    )

    # Start notification polling task
    async def notification_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        await check_and_send_notifications(context)

    interval = float(os.getenv("BOT_NOTIFICATION_POLL_INTERVAL_SECONDS", "60"))
    app.job_queue.run_repeating(
        notification_job,
        interval=interval,
        first=1,  # Start after 1 second
    )
    logger.info(f"Notification polling task scheduled every {interval:.1f}s secs...")

    logger.info("Bot started and ready to receive messages - starting polling...")
    app.run_polling()
