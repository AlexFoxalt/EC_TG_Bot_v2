from sqlalchemy import select
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_main_keyboard, get_notification_choice_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update
from src.db.models import User
from src.logger.main import logger


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - check if user exists, register if new."""
    user = update.effective_user
    if user is None:
        logger.warning("Received /start command but effective_user is None")
        return
    u_identity = get_user_identity_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    logger.bind(username=u_identity).info("Received /start command from user")

    async with session_factory() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.id == user.id))
        existing_user: User | None = result.scalar_one_or_none()

        welcome_msg = langpack.MSG_WELCOME_USER.format(username=user.first_name or user.username or langpack.WORD_USER)
        if existing_user:
            await update.message.reply_text(
                f"{welcome_msg}\n\n{langpack.MSG_USE_KEYBOARD}",
                reply_markup=get_main_keyboard(langpack),
            )
            if existing_user.language_code != user.language_code:
                logger.info(
                    f"Updating language for user user_id={user.id}: {existing_user.language_code} > {user.language_code}"
                )
                existing_user.language_code = user.language_code
                await session.commit()
            return

        # New user - create user record
        logger.info(f"New user detected user_id={user.id} -> Creating new DB record...")
        new_user = User(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            is_bot=user.is_bot,
            language_code=user.language_code,
            is_admin=False,
            notifs_enabled=True,  # Default, will be updated by user choice
            night_notif_sound_enabled=True,  # Default, will be updated by user choice
        )
        session.add(new_user)
        await session.commit()
        logger.info(
            f"User record created successfully: "
            f"user_id={new_user.id}, "
            f"username={new_user.username}, "
            f"first_name={new_user.first_name}, "
            f"is_bot={new_user.is_bot}, "
            f"language_code={new_user.language_code}, "
            f"is_admin={new_user.is_admin}"
        )

        # Ask about notifications

        await update.message.reply_text(
            f"{welcome_msg}\n\n{langpack.MSG_Q_ENABLE_NOTIFS}",
            reply_markup=get_notification_choice_keyboard(langpack),
        )

        # Store user_id in context for callback handlers
        context.user_data["registering_user_id"] = user.id
        logger.info(f"Started registration flow for user_id={user.id} - waiting for notification preference...")
