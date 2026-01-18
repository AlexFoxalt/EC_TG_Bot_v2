import asyncio
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from aiolimiter import AsyncLimiter

from src.db.models import User, Status
from src.logger.main import logger
from src.utils import _require_env, get_database_url


if TYPE_CHECKING:
    from telegram.ext import Application

# Constants
KYIV_TZ = ZoneInfo("Europe/Kyiv")
NIGHT_START_HOUR = 20  # 20:00 Ukraine time
NIGHT_END_HOUR = 6  # 06:00 Ukraine time
SECS_IN_MINUTE = 60
MINS_IN_HOUR = 60

# Button texts
BUTTON_GET_STATUS = "💡 Узнать статус 💡"
BUTTON_SETTINGS = "⚙️ Настройки ⚙️"
BUTTON_REPORT_ERROR = "🆘 Сообщить об ошибке 🆘"

# Error messages
ERROR_BOT_NOT_INITIALIZED = "Бот некорректно инициализирован. Пожалуйста, свяжитесь с администратором."
ERROR_USER_NOT_FOUND = "Пользователь не найден. Пожалуйста, используйте команду /start еще раз."
ERROR_SESSION_EXPIRED = "Срок жизни сессии истек. Пожалуйста, воспользуйтесь командой /start заново."

# Global state - will be initialized in start_bot()
session_factory: async_sessionmaker[AsyncSession] | None = None
bot_app: Application | None = None
last_notified_status_id: int | None = None
notification_rate_limiter: AsyncLimiter | None = None
notification_semaphore: asyncio.Semaphore | None = None


def _is_retryable_telegram_exception(exc: Exception) -> bool:
    """Check if exception is retryable (transient network/API errors for Telegram)."""
    # Retry on network-related errors
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
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


# Helper functions
def get_username_from_update(update: Update) -> str:
    """Extract username from update for logging."""
    user = update.effective_user
    if user is None:
        return "unknown"
    return user.username or user.first_name or f"user_{user.id}" or "unknown"


def get_username_from_user_id(user_id: int | None) -> str:
    """Get username from user_id for logging."""
    if user_id is None:
        return "unknown"
    return f"user_{user_id}"


def get_username_from_query(query) -> str:
    """Extract username from callback query for logging."""
    if query is None or query.from_user is None:
        return "unknown"
    user = query.from_user
    return user.username or user.first_name or f"user_{user.id}" or "unknown"


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get the main persistent keyboard for registered users."""
    keyboard = [
        [KeyboardButton(BUTTON_GET_STATUS)],
        [KeyboardButton(BUTTON_SETTINGS), KeyboardButton(BUTTON_REPORT_ERROR)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_notification_choice_keyboard() -> InlineKeyboardMarkup:
    """Get inline keyboard for notification preference choice."""
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="notif_yes"),
            InlineKeyboardButton("Нет", callback_data="notif_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_night_sound_choice_keyboard() -> InlineKeyboardMarkup:
    """Get inline keyboard for night sound preference choice."""
    keyboard = [
        [
            InlineKeyboardButton("🔊ВКЛЮЧИТЬ звук ночью", callback_data="night_sound_yes"),
            InlineKeyboardButton("🔇ВЫКЛЮЧИТЬ звук ночью", callback_data="night_sound_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def is_night_time() -> bool:
    """Check if current time is night time (20:00 - 06:00 UTC, which is 22:00 - 08:00 Kyiv time)."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


async def get_user_from_db(user_id: int) -> User | None:
    """Get user from database by ID."""
    if session_factory is None:
        return None
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


def get_completion_message(
    is_reconfiguration: bool, notifications_enabled: bool, night_sound_enabled: bool | None = None
) -> str:
    """Get completion message based on flow type and settings."""
    if not notifications_enabled:
        return (
            "Уведомления отключены. Вы можете изменить это позже.\n\nНастройки обновлены ✅"
            if is_reconfiguration
            else "Уведомления отключены. Вы можете изменить это позже.\n\nРегистрация завершена! Теперь Вы можете использовать бота 🎉"
        )

    if night_sound_enabled is not None:
        sound_status = "включено" if night_sound_enabled else "выключено"
        emoji = "🔊" if night_sound_enabled else "🔇"
        return (
            f"Звуковое оповещение в ночное время {sound_status} {emoji}\n\nНастройки обновлены ✅"
            if is_reconfiguration
            else f"Звуковое оповещение в ночное время {sound_status} {emoji}\n\nРегистрация завершена! Теперь Вы можете использовать бота 🎉"
        )

    return ""


async def cleanup_registration_context(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Clean up registration/reconfiguration context and log completion."""
    is_reconfiguration = context.user_data.get("is_reconfiguration", False)
    context.user_data.pop("registering_user_id", None)
    context.user_data.pop("is_reconfiguration", None)
    logger.bind(username="system").info(
        f"{'Settings reconfiguration' if is_reconfiguration else 'Registration'} flow for user_id={user_id} completed"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - check if user exists, register if new."""
    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized - bot not properly started")
        await update.message.reply_text(ERROR_BOT_NOT_INITIALIZED)
        return

    user = update.effective_user
    if user is None:
        logger.bind(username="unknown").warning("Received /start command but effective_user is None")
        return

    username = get_username_from_update(update)
    logger.bind(username=username).info("Received /start command from user")

    async with session_factory() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.id == user.id))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            await update.message.reply_text(
                f"Добро пожаловать, {user.first_name or user.username or 'Пользователь'}!",
                reply_markup=get_main_keyboard(),
            )
            return

        # New user - create user record
        logger.bind(username="system").info(f"New user detected user_id={user.id} -> Creating new DB record...")
        new_user = User(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            is_bot=user.is_bot,
            language_code=user.language_code,
            id_admin=False,
            notifs_enabled=True,  # Default, will be updated by user choice
            night_notif_sound_enabled=True,  # Default, will be updated by user choice
        )
        session.add(new_user)
        await session.commit()
        logger.bind(username="system").info(
            f"User record created successfully: "
            f"user_id={new_user.id}, "
            f"username={new_user.username}, "
            f"first_name={new_user.first_name}, "
            f"is_bot={new_user.is_bot}, "
            f"language_code={new_user.language_code}, "
            f"is_admin={new_user.id_admin}"
        )

        # Ask about notifications
        await update.message.reply_text(
            f"Добро пожаловать, {user.first_name or user.username or 'Пользователь'}! 👋\n\n"
            "Хотите включить уведомления (бот самостоятельно будет отправлять сообщение в чат, "
            "в моменты когда свет включают/выключают)?",
            reply_markup=get_notification_choice_keyboard(),
        )

        # Store user_id in context for callback handlers
        context.user_data["registering_user_id"] = user.id
        logger.bind(username="system").info(
            f"Started registration flow for user_id={user.id} - waiting for notification preference..."
        )


async def handle_notification_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's choice about notifications."""
    query = update.callback_query
    username = get_username_from_query(query)

    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_notification_choice")
        return

    if query is None:
        logger.bind(username="system").warning("Received notification choice callback but query is None")
        return

    await query.answer()

    user_id = context.user_data.get("registering_user_id")
    if user_id is None:
        callback_user_id = query.from_user.id if query.from_user else "unknown"
        logger.bind(username=username).warning(
            f"Notification choice received but no registering_user_id in context. "
            f"Callback from user_id={callback_user_id}"
        )
        await query.edit_message_text(ERROR_SESSION_EXPIRED)
        return

    # Determine if notifications are enabled
    notifs_enabled = query.data == "notif_yes"
    logger.bind(username=username).info(f"Selected notifications: {notifs_enabled} (callback_data={query.data})")

    user = await get_user_from_db(user_id)
    if user is None:
        logger.bind(username="system").error("User not found in database during notification choice update")
        await query.edit_message_text(ERROR_USER_NOT_FOUND)
        return

    # Update user notification preference
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.notifs_enabled = notifs_enabled
            await session.commit()
            logger.bind(username="system").info(f"Updated user user_id={user_id}: notifs_enabled={notifs_enabled}")

    if notifs_enabled:
        # Ask about night notification sound
        await query.edit_message_text(
            "Отлично! Уведомления включены. 🔔\n\n"
            "Хотите выключить звук для ночных уведомлений (уведомления, которые приходят в ночное время "
            "в период 22:00 - 08:00 будут приходить беззвучно)?",
            reply_markup=get_night_sound_choice_keyboard(),
        )
        logger.bind(username="system").info(f"Waiting for night sound preference from user_id={user_id} ...")
    else:
        is_reconfiguration = context.user_data.get("is_reconfiguration", False)
        completion_text = get_completion_message(is_reconfiguration, notifications_enabled=False)
        await query.edit_message_text(completion_text)
        await query.message.reply_text(
            "Используйте клавиатуру ниже для взаимодействия с ботом 👇", reply_markup=get_main_keyboard()
        )
        await cleanup_registration_context(context, user_id)


async def handle_night_sound_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's choice about night notification sound."""
    query = update.callback_query
    username = get_username_from_query(query)

    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_night_sound_choice")
        return

    if query is None:
        logger.bind(username="system").warning("Received night sound choice callback but query is None")
        return

    await query.answer()

    user_id = context.user_data.get("registering_user_id")
    if user_id is None:
        callback_user_id = query.from_user.id if query.from_user else "unknown"
        logger.bind(username=username).warning(
            f"Night sound choice received but no registering_user_id in context. "
            f"Callback from user_id={callback_user_id}"
        )
        await query.edit_message_text(ERROR_SESSION_EXPIRED)
        return

    # Determine if night sound is enabled
    night_sound_enabled = query.data == "night_sound_yes"
    logger.bind(username=username).info(f"Selected night sound: {night_sound_enabled} (callback_data={query.data})")

    user = await get_user_from_db(user_id)
    if user is None:
        logger.bind(username=username).error("User not found in database during night sound choice update")
        await query.edit_message_text(ERROR_USER_NOT_FOUND)
        return

    # Update user night sound preference
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.night_notif_sound_enabled = night_sound_enabled
            await session.commit()
            logger.bind(username="system").info(
                f"User updated user_id={db_user.id}: night_notif_sound_enabled={night_sound_enabled}"
            )

    is_reconfiguration = context.user_data.get("is_reconfiguration", False)
    completion_text = get_completion_message(
        is_reconfiguration, notifications_enabled=True, night_sound_enabled=night_sound_enabled
    )
    await query.edit_message_text(completion_text)
    await query.message.reply_text(
        "Используйте клавиатуру ниже для взаимодействия с ботом.", reply_markup=get_main_keyboard()
    )
    await cleanup_registration_context(context, user_id)


async def handle_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Notification settings' button - allow user to reconfigure notification preferences."""

    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_notification_settings")
        await update.message.reply_text(ERROR_BOT_NOT_INITIALIZED)
        return

    user = update.effective_user
    if user is None:
        logger.bind(username="system").warning("Received notification settings request but effective_user is None")
        return

    username = get_username_from_update(update)
    logger.bind(username=username).info("User requested to reconfigure notification settings")

    # Verify user exists in database
    existing_user = await get_user_from_db(user.id)
    if existing_user is None:
        logger.bind(username=username).warning("User not found in database - redirecting to /start")
        await update.message.reply_text(
            "Пользователь не найден. Пожалуйста, используйте команду /start для регистрации.",
            reply_markup=get_main_keyboard(),
        )
        return

    # Start the notification preference flow (reuse registration flow)
    await update.message.reply_text(
        "Хотите включить уведомления (бот самостоятельно будет отправлять сообщение в чат, "
        "в моменты когда свет включают/выключают)?",
        reply_markup=get_notification_choice_keyboard(),
    )

    # Store user_id in context for callback handlers (same as registration flow)
    context.user_data["registering_user_id"] = user.id
    context.user_data["is_reconfiguration"] = True  # Mark as reconfiguration
    logger.bind(username="system").info(
        f"Started notification settings reconfiguration for user_id={user.id} - waiting for notification preference..."
    )


async def handle_report_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Report Error' button."""
    user = update.effective_user
    if user is None:
        logger.bind(username="system").warning("Received report error request but effective_user is None")
        return

    username = get_username_from_update(update)

    logger.bind(username=username).info("User requested to report an error")
    await update.message.reply_text(
        "Если у Вас что-то не работает, то напишите мне в личку, все починим и настроим 🤝\n\n@AlexFoxalt",
        reply_markup=get_main_keyboard(),
    )


async def handle_get_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Get status' button - retrieve latest electricity status."""
    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(ERROR_BOT_NOT_INITIALIZED)
        return

    user = update.effective_user
    if user is None:
        logger.bind(username="system").warning("Received get status request but effective_user is None")
        return

    username = get_username_from_update(update)
    logger.bind(username=username).info("User requested electricity status")

    async with session_factory() as session:
        # Get latest status ordered by date_created DESC
        result = await session.execute(select(Status).order_by(desc(Status.date_created)).limit(1))
        latest_status = result.scalar_one_or_none()

        if latest_status is None:
            logger.bind(username=username).warning("No status records found in database")
            await update.message.reply_text(
                "⚠️ Информация пока недоступна. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_keyboard(),
            )
            return

        # Determine status message
        is_on = latest_status.value
        status_text = "🟢 Электричество ЕСТЬ! 🟢" if is_on else "🔴 Электричества НЕТ 🔴"
        datetime_text = "📅 Время включения: " if is_on else "📅 Время отключения: "
        date_created_timezone = latest_status.date_created.astimezone(KYIV_TZ)
        logger.bind(username="system").info(
            f"Retrieved latest status value={is_on}, date_created={latest_status.date_created}"
        )

        await update.message.reply_text(
            f"{status_text}\n\n{datetime_text}{date_created_timezone:%H:%M %d.%m.%Y }",
            reply_markup=get_main_keyboard(),
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception(_is_retryable_telegram_exception),
    reraise=True,  # Reraise after retries - we'll catch in outer function
    before_sleep=before_sleep_log(logger.bind(username="system"), "WARNING"),
)
async def _send_message_with_retry(user_id: int, message_text: str, disable_sound: bool) -> None:
    """Internal function to send message with retry logic.

    Retries up to 3 times on transient errors (network, timeouts, rate limits).
    Uses exponential backoff: 1s, 2s, 4s (max 5s).
    """
    if bot_app is None:
        raise RuntimeError("Bot application not initialized")
    if notification_rate_limiter is None or notification_semaphore is None:
        raise RuntimeError("Notification limiter not initialized")

    async with notification_semaphore:
        async with notification_rate_limiter:
            await bot_app.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_notification=disable_sound,
            )


async def send_status_notification(
    user_id: int, from_status: bool, to_status: bool, time_diff: int | None, disable_sound: bool = False
) -> None:
    """Send status change notification to a user with retry logic.

    This function will retry up to 3 times on transient errors (network, timeouts, etc.)
    but will not break the notification loop if it ultimately fails.
    """
    if bot_app is None:
        logger.bind(username="system").error("Bot application not initialized - cannot send notification")
        return

    to_text = "ON" if to_status else "OFF"
    to_emoji = "🟢" if to_status else "🔴"

    changes_text = f"📢️  ВНИМАНИЕ  📢\n\n{to_emoji}  Электричество {to_text}  {to_emoji}\n"

    time_diff_text = ""
    if time_diff:
        diff_mins = time_diff // SECS_IN_MINUTE
        if diff_mins > MINS_IN_HOUR:
            # Convert minutes to hours if it's possible.
            # "100500 mins elapsed" message looks weird.
            diff_hours = diff_mins // MINS_IN_HOUR
            diff_mins = diff_mins % MINS_IN_HOUR

            if diff_mins == 0:
                text_suffix = f"{diff_hours} ч\\."
            else:
                text_suffix = f"{diff_hours} ч\\. и {diff_mins} мин\\."
        else:
            text_suffix = f"{diff_mins} мин\\."

        if from_status and not to_status:
            time_diff_text = f"⏳Свет был {text_suffix}\n\n"
        elif not from_status and to_status:
            time_diff_text = f"⏳Света не было {text_suffix}\n\n"

    footer_text = (
        "_Вы получили это сообщение потому что включили уведомления в настройках бота\\. "
        "Их можно в любой момент отключить\\._"
    )
    final_text = changes_text + time_diff_text + footer_text

    try:
        await _send_message_with_retry(user_id, final_text, disable_sound)
        logger.bind(username="system").info(
            f"Sent status notification to user_id={user_id}, sound_disabled={disable_sound}"
        )
    except Exception as e:
        # Final failure after all retries - log but don't raise to continue loop
        logger.bind(username="system").error(f"Failed to send notification to user_id={user_id} after retries: {e!r}")


async def _send_notification_task(
    user: User,
    previous_status: Status,
    latest_status: Status,
    time_diff: int | None,
    is_night: bool,
) -> None:
    if notification_rate_limiter is None or notification_semaphore is None:
        logger.bind(username="system").error("Notification limiter not initialized - skipping send task")
        return

    try:
        disable_sound = is_night and not user.night_notif_sound_enabled
        await send_status_notification(
            user_id=user.id,
            from_status=previous_status.value,
            to_status=latest_status.value,
            time_diff=time_diff,
            disable_sound=disable_sound,
        )
    except Exception as e:
        logger.bind(username="system").error(f"Notification task failed for user_id={user.id}: {e!r}")
        return


async def check_and_send_notifications() -> None:
    """Check for new status changes and send notifications to enabled users."""
    global last_notified_status_id

    if session_factory is None:
        logger.bind(username="system").warning("Session factory not initialized - skipping notification check")
        return

    if bot_app is None:
        logger.bind(username="system").warning("Bot application not initialized - skipping notification check")
        return

    try:
        async with session_factory() as session:
            # Get the two most recent statuses to determine the change
            result = await session.execute(select(Status).order_by(desc(Status.date_created)).limit(2))
            statuses = result.scalars().all()

            if not statuses:
                logger.bind(username="system").debug("No status records found - skipping notification check")
                return

            latest_status = statuses[0]
            previous_status = statuses[1] if len(statuses) > 1 else None

            # Set init value on app start
            if last_notified_status_id is None:
                last_notified_status_id = latest_status.id

            # Check if we've already notified about this status
            if last_notified_status_id is not None and latest_status.id == last_notified_status_id:
                return

            # If this is the first status or status hasn't changed, don't notify
            if previous_status is None or latest_status.value == previous_status.value:
                last_notified_status_id = latest_status.id
                return

            # Status has changed - get all users with notifications enabled
            users_result = await session.execute(select(User).where(User.notifs_enabled == True))  # noqa
            users = users_result.scalars().all()

            if not users:
                logger.bind(username="system").info("No users with notifications enabled - skipping notification send")
                last_notified_status_id = latest_status.id
                return

            # Determine if it's night time
            is_night = is_night_time()
            logger.bind(username="system").info(
                f"Status change detected: {previous_status.value} → {latest_status.value}, "
                f"is_night={is_night}, notifying {len(users)} users"
            )

            time_diff = None
            if latest_status and previous_status:
                time_diff = (latest_status.date_created - previous_status.date_created).seconds

            # Send notifications to all enabled users concurrently with rate limiting
            tasks = [
                asyncio.create_task(_send_notification_task(user, previous_status, latest_status, time_diff, is_night))
                for user in users
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.bind(username="system").error(
                        f"Notification task failed with unexpected exception: {result!r}"
                    )

            # Update last notified status ID
            last_notified_status_id = latest_status.id
            logger.bind(username="system").info(
                f"Notifications sent for status change, last_notified_status_id={last_notified_status_id}"
            )

    except Exception as e:
        logger.bind(username="system").error(f"Error in check_and_send_notifications: {e!r}", exc_info=True)


def start_bot() -> None:
    """Initialize and start the Telegram bot."""
    global session_factory, bot_app, notification_rate_limiter, notification_semaphore

    logger.bind(username="system").info("Initializing Telegram bot...")

    # Create database session factory
    database_url = get_database_url()
    logger.bind(username="system").info("Creating database engine connection (host from env)")
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    logger.bind(username="system").info("Database session factory created successfully")

    app = ApplicationBuilder().token(_require_env("TELEGRAM_TOKEN")).build()
    bot_app = app  # Store for notification sending
    logger.bind(username="system").info("Telegram application builder initialized")

    rate_limit_per_sec = float(os.getenv("BOT_NOTIF_RATE_LIMIT_PER_SEC", "20"))
    max_concurrency = int(os.getenv("BOT_NOTIF_MAX_CONCURRENCY", "10"))
    if rate_limit_per_sec <= 0:
        rate_limit_per_sec = 1.0
    if max_concurrency <= 0:
        max_concurrency = 1
    notification_rate_limiter = AsyncLimiter(rate_limit_per_sec, time_period=1)
    notification_semaphore = asyncio.Semaphore(max_concurrency)
    logger.bind(username="system").info(
        f"Notification rate limiting configured: {rate_limit_per_sec:.1f}/s, max_concurrency={max_concurrency}"
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_notification_choice, pattern="^notif_(yes|no)$"))
    app.add_handler(CallbackQueryHandler(handle_night_sound_choice, pattern="^night_sound_(yes|no)$"))
    app.add_handler(MessageHandler(filters.Regex(f"^{BUTTON_GET_STATUS}$"), handle_get_status))
    app.add_handler(MessageHandler(filters.Regex(f"^{BUTTON_SETTINGS}$"), handle_notification_settings))
    app.add_handler(MessageHandler(filters.Regex(f"^{BUTTON_REPORT_ERROR}$"), handle_report_error))

    # Start notification polling task
    async def notification_job(_: ContextTypes.DEFAULT_TYPE) -> None:
        await check_and_send_notifications()

    interval = float(os.getenv("BOT_NOTIFICATION_POLL_INTERVAL_SECONDS", "60"))
    app.job_queue.run_repeating(
        notification_job,
        interval=interval,
        first=1,  # Start after 1 second
    )
    logger.bind(username="system").info(f"Notification polling task scheduled every {interval:.1f}s secs...")

    logger.bind(username="system").info("Bot started and ready to receive messages - starting polling...")
    app.run_polling()
