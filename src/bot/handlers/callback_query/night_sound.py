from sqlalchemy import select
from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import (
    get_user_identity_from_query,
    get_user_from_db,
    get_completion_message,
    cleanup_registration_context,
)
from src.db.models import User
from src.logger.main import logger


async def handle_night_sound_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's choice about night notification sound."""
    query = update.callback_query
    if query is None:
        logger.warning("Received night sound choice callback but query is None")
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
        logger.bind(username=u_identity).warning("Night sound choice received but no registering_user_id in context")
        await query.edit_message_text(langpack.ERR_SESSION_EXPIRED)
        return

    # Determine if night sound is enabled
    night_sound_enabled = query.data == "night_sound_yes"
    logger.bind(username=u_identity).info(f"Selected night sound: {night_sound_enabled} (callback_data={query.data})")

    user = await get_user_from_db(session_factory, user_id)
    if user is None:
        logger.bind(username=u_identity).error("User not found in db during night sound choice update")
        await query.edit_message_text(langpack.ERR_USER_NOT_FOUND)
        return

    # Update user night sound preference
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.night_notif_sound_enabled = night_sound_enabled
            await session.commit()
            logger.bind(username=u_identity).info(f"User updated: night_notif_sound_enabled={night_sound_enabled}")

    is_reconfiguration = context.user_data.get("is_reconfiguration", False)
    completion_text = get_completion_message(
        langpack, is_reconfiguration, notifications_enabled=True, night_sound_enabled=night_sound_enabled
    )
    await query.edit_message_text(completion_text)
    await query.message.reply_text(langpack.MSG_USE_KEYBOARD, reply_markup=get_main_keyboard(langpack))
    await cleanup_registration_context(context, u_identity)
