import asyncio

from sqlalchemy import select
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_username_from_update, send_message_with_retry
from src.db.models import User
from src.logger.main import logger


async def msg_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /msg_all admin command."""
    user = update.effective_user
    if user is None:
        logger.bind(username="system").warning("Received /msg_all command but effective_user is None")
        return

    username = get_username_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
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

    logger.bind(username=username).info("Received /msg_all command from user")

    async with session_factory() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.id == user.id))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            logger.bind(username="system").warning(f"User with ID {user.id} not found in DB")
            return

        if not existing_user.is_admin:
            logger.bind(username="system").warning(f"User with ID {user.id} requested forbidden command /msgAll")
            return

        result = await session.execute(select(User))
        all_users = result.scalars().all()

    message = update.message.text.replace("/msgAll ", "")
    tasks = [
        asyncio.create_task(
            send_message_with_retry(
                bot_app=bot_app,
                rate_limiter=rate_limiter,
                semaphore=semaphore,
                user_id=recipient.id,
                message_text=message,
                disable_sound=False,
            )
        )
        for recipient in all_users
        if recipient.id != user.id
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.bind(username="system").error(f"Notification task failed with unexpected exception: {result!r}")

    logger.bind(username="system").info(f"Admin message successfully sent to {len(all_users)} users")
    await update.message.reply_text(
        f"Message successfully sent to {len(all_users)} users",
        reply_markup=get_main_keyboard(langpack),
    )
