from sqlalchemy import select, desc
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
)

from src.bot.constants import KYIV_TZ
from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_user_identity_from_update
from src.db.models import Status
from src.enums import Label
from src.logger.main import logger


async def handle_power_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        logger.warning("Received power status request but effective_user is None")
        return
    u_identity = get_user_identity_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    logger.bind(username=u_identity).info("User requested electricity status")

    async with session_factory() as session:
        # Get latest status ordered by date_created DESC
        power_label = str(Label.power)
        result = await session.execute(
            select(Status).where(Status.label == power_label).order_by(desc(Status.date_created)).limit(1)
        )
        latest_status = result.scalar_one_or_none()

        if latest_status is None:
            logger.bind(username=u_identity).warning("No status records of Status found in DB")
            await update.message.reply_text(
                langpack.MSG_POWER_STATUS_NOT_AVAILABLE,
                reply_markup=get_main_keyboard(langpack),
            )
            return

        # Determine status message
        is_on = latest_status.value
        status_text = langpack.MSG_POWER_IS_ON if is_on else langpack.MSG_POWER_IS_OFF
        datetime_text = langpack.MSG_POWER_TURN_ON_TIME if is_on else langpack.MSG_POWER_TURN_OFF_TIME
        date_created_timezone = latest_status.date_created.astimezone(KYIV_TZ)
        logger.info(
            f"Retrieved latest [{power_label}] status value={is_on}, date_created={latest_status.date_created.isoformat()}"
        )

        await update.message.reply_text(
            f"{status_text}\n\n{datetime_text}{date_created_timezone:%H:%M %d\\.%m\\.%Y }",
            reply_markup=get_main_keyboard(langpack),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
