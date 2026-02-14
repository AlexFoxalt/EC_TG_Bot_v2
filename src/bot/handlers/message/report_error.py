from telegram import Update
from telegram.ext import (
    ContextTypes,
)

from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update, button_rate_limited
from src.logger.main import logger


@button_rate_limited
async def handle_report_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Report Error' button."""
    user = update.effective_user
    if user is None:
        logger.warning("Received report error request but effective_user is None")
        return

    u_identity = get_user_identity_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    logger.bind(username=u_identity).info("🆘 User requested to report an error")
    await update.message.reply_text(
        langpack.MSG_REPORT_ERROR,
        reply_markup=get_main_keyboard(langpack),
    )
