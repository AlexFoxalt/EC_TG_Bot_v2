from sqlalchemy import select
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_night_sound_choice_keyboard, get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import (
    get_user_identity_from_query,
    get_user_from_db,
    get_completion_message,
    cleanup_registration_context,
)
from src.db.models import User
from src.logger.main import logger


async def handle_notification_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's choice about notifications."""
    query = update.callback_query
    if query is None:
        logger.warning("Received notification choice callback but query is None")
        return

    u_identity = get_user_identity_from_query(query)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username=u_identity).error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    await query.answer()

    user_id = context.user_data.get("registering_user_id")
    if user_id is None:
        logger.bind(username=u_identity).warning("Notification choice received but no registering_user_id in context")
        await query.edit_message_text(langpack.ERR_SESSION_EXPIRED)
        return

    # Determine if notifications are enabled
    notifs_enabled = query.data == "notif_yes"
    logger.bind(username=u_identity).info(f"Selected notifications: {notifs_enabled} (callback_data={query.data})")

    user = await get_user_from_db(session_factory, user_id)
    if user is None:
        logger.bind(username=u_identity).error("User not found in db during notification choice update")
        await query.edit_message_text(langpack.ERR_USER_NOT_FOUND)
        return

    # Update user notification preference
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.notifs_enabled = notifs_enabled
            await session.commit()
            logger.bind(username=u_identity).info(f"User updated: notifs_enabled={notifs_enabled}")

    if notifs_enabled:
        # Ask about night notification sound
        await query.edit_message_text(
            langpack.MSG_NOTIFICATIONS_ON,
            reply_markup=get_night_sound_choice_keyboard(langpack),
        )
        logger.bind(username=u_identity).info("Waiting for night sound preference from user...")
    else:
        is_reconfiguration = context.user_data.get("is_reconfiguration", False)
        completion_text = get_completion_message(langpack, is_reconfiguration, notifications_enabled=False)
        await query.edit_message_text(completion_text)
        await query.message.reply_text(langpack.MSG_USE_KEYBOARD, reply_markup=get_main_keyboard(langpack))
        await cleanup_registration_context(context, u_identity)
