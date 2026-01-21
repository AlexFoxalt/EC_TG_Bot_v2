import asyncio

from aiolimiter import AsyncLimiter
from telegram.ext import ContextTypes, Application
from sqlalchemy import select, desc

from src.bot.constants import MINS_IN_HOUR, SECS_IN_MINUTE
from src.bot.lang_pack.base import BaseLangPack
from src.bot.lang_pack.container import LangContainer
from src.bot.utils import send_message_with_retry, is_nighttime
from src.db.models import User, Status
from src.enums import Label
from src.logger.main import logger


async def _send_status_notification(
    rate_limiter: AsyncLimiter,
    semaphore: asyncio.Semaphore,
    bot_app: Application,
    langpack: BaseLangPack,
    user_id: int,
    from_status: bool,
    to_status: bool,
    time_diff: int | None,
    disable_sound: bool = False,
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

    changes_text = f"{langpack.NOTIF_ATTENTION}\n\n{to_emoji}  {langpack.WORD_ELECTRICITY} {to_text}  {to_emoji}\n"

    time_diff_text = ""
    if time_diff:
        diff_mins = time_diff // SECS_IN_MINUTE
        if diff_mins > MINS_IN_HOUR:
            # Convert minutes to hours if it's possible.
            # "100500 mins elapsed" message looks weird.
            diff_hours = diff_mins // MINS_IN_HOUR
            diff_mins = diff_mins % MINS_IN_HOUR

            if diff_mins == 0:
                text_suffix = f"{diff_hours} {langpack.WORD_HOURS}\\."
            else:
                text_suffix = (
                    f"{diff_hours} {langpack.WORD_HOURS}\\. {langpack.WORD_AND} {diff_mins} {langpack.WORD_MINUTES}\\."
                )
        else:
            text_suffix = f"{diff_mins} {langpack.WORD_MINUTES}\\."

        if from_status and not to_status:
            time_diff_text = f"{langpack.NOTIF_POWER_TURN_ON_TIME} {text_suffix}\n\n"
        elif not from_status and to_status:
            time_diff_text = f"{langpack.NOTIF_POWER_TURN_OFF_TIME} {text_suffix}\n\n"

    final_text = changes_text + time_diff_text + langpack.NOTIF_FOOTER

    try:
        await send_message_with_retry(rate_limiter, semaphore, user_id, final_text, disable_sound)
        logger.bind(username="system").info(
            f"Sent status notification to user_id={user_id}, sound_disabled={disable_sound}"
        )
    except Exception as e:
        # Final failure after all retries - log but don't raise to continue loop
        logger.bind(username="system").error(f"Failed to send notification to user_id={user_id} after retries: {e!r}")


async def _send_notification_task(
    bot_app: Application,
    rate_limiter: AsyncLimiter,
    semaphore: asyncio.Semaphore,
    languages: LangContainer,
    user: User,
    previous_status: Status,
    latest_status: Status,
    time_diff: int | None,
    is_night: bool,
) -> None:
    try:
        langpack = languages.from_langcode(user.language_code)
        disable_sound = is_night and not user.night_notif_sound_enabled
        await _send_status_notification(
            bot_app=bot_app,
            rate_limiter=rate_limiter,
            semaphore=semaphore,
            langpack=langpack,
            user_id=user.id,
            from_status=previous_status.value,
            to_status=latest_status.value,
            time_diff=time_diff,
            disable_sound=disable_sound,
        )
    except Exception as e:
        logger.bind(username="system").error(f"Notification task failed for user_id={user.id}: {e!r}")
        return


async def check_and_send_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for new status changes and send notifications to enabled users."""
    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized - skipping notification check")
        return

    bot_app = context.application.bot_data["app"]
    if bot_app is None:
        logger.bind(username="system").error("Bot application not initialized - skipping notification check")
        return

    rate_limiter = context.application.bot_data["rate_limiter"]
    if rate_limiter is None:
        logger.bind(username="system").error("Rate limiter not initialized - skipping notification check")
        return

    semaphore = context.application.bot_data["semaphore"]
    if semaphore is None:
        logger.bind(username="system").error("Semaphore not initialized - skipping notification check")
        return

    languages = context.application.bot_data["languages"]
    if languages is None:
        logger.bind(username="system").error("Languages not initialized - skipping notification check")
        return

    try:
        async with session_factory() as session:
            # Get the two most recent statuses to determine the change
            power_label = str(Label.power)
            result = await session.execute(
                select(Status).where(Status.label == power_label).order_by(desc(Status.date_created)).limit(2)
            )
            statuses = result.scalars().all()

            if not statuses:
                logger.bind(username="system").debug(
                    f"No status records with label: {power_label} found - skipping notification check"
                )
                return

            latest_status = statuses[0]
            previous_status = statuses[1] if len(statuses) > 1 else None

            # Set init value on app start
            if context.application.bot_data["last_notified_status_id"] is None:
                context.application.bot_data["last_notified_status_id"] = latest_status.id

            # Check if we've already notified about this status
            if (
                context.application.bot_data["last_notified_status_id"] is not None
                and latest_status.id == context.application.bot_data["last_notified_status_id"]
            ):
                return

            # If this is the first status or status hasn't changed, don't notify
            if previous_status is None or latest_status.value == previous_status.value:
                context.application.bot_data["last_notified_status_id"] = latest_status.id
                return

            # Status has changed - get all users with notifications enabled
            users_result = await session.execute(select(User).where(User.notifs_enabled == True))  # noqa
            users = users_result.scalars().all()

            if not users:
                logger.bind(username="system").info("No users with notifications enabled - skipping notification send")
                context.application.bot_data["last_notified_status_id"] = latest_status.id
                return

            # Determine if it's night time
            is_night = is_nighttime()
            logger.bind(username="system").info(
                f"Status change detected: {previous_status.value} → {latest_status.value}, "
                f"is_night={is_night}, notifying {len(users)} users"
            )

            time_diff = None
            if latest_status and previous_status:
                time_diff = (latest_status.date_created - previous_status.date_created).seconds

            # Send notifications to all enabled users concurrently with rate limiting
            tasks = [
                asyncio.create_task(
                    _send_notification_task(
                        bot_app=bot_app,
                        rate_limiter=rate_limiter,
                        semaphore=semaphore,
                        user=user,
                        languages=languages,
                        previous_status=previous_status,
                        latest_status=latest_status,
                        time_diff=time_diff,
                        is_night=is_night,
                    )
                )
                for user in users
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.bind(username="system").error(
                        f"Notification task failed with unexpected exception: {result!r}"
                    )

            # Update last notified status ID
            context.application.bot_data["last_notified_status_id"] = latest_status.id
            logger.bind(username="system").info(
                f"Notifications sent for status change, last_notified_status_id={context.application.bot_data['last_notified_status_id']}"
            )

    except Exception as e:
        logger.bind(username="system").error(f"Error in check_and_send_notifications: {e!r}", exc_info=True)
