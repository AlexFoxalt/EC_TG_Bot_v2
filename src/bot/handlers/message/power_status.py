from datetime import datetime, UTC

from sqlalchemy import select, desc
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
)

from src.bot.constants import KYIV_TZ, SECS_IN_MINUTE, MINS_IN_HOUR
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
        logger.bind(username=u_identity).error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    logger.bind(username=u_identity).info("💡User requested power status")

    async with session_factory() as session:
        # Get latest status ordered by date_created DESC
        power_label = str(Label.power)
        result = await session.execute(
            select(Status).where(Status.label == power_label).order_by(desc(Status.date_created)).limit(1)
        )
        latest_status = result.scalar_one_or_none()
        logger.bind(username=u_identity).info(
            f"Retrieved latest [{power_label}] status value={latest_status.value}, date_created={latest_status.date_created.isoformat()}"
        )

    if latest_status is None:
        logger.bind(username=u_identity).warning(f"No status Status record with label [{power_label}] found in DB")
        await update.message.reply_text(
            langpack.MSG_POWER_STATUS_NOT_AVAILABLE,
            reply_markup=get_main_keyboard(langpack),
        )
        return

    curr_time = datetime.now(UTC)
    time_diff = int((curr_time - latest_status.date_created).total_seconds())

    # Determine status message
    is_on = latest_status.value
    status_text = langpack.MSG_POWER_IS_ON if is_on else langpack.MSG_POWER_IS_OFF
    datetime_text = langpack.MSG_POWER_TURN_ON_TIME if is_on else langpack.MSG_POWER_TURN_OFF_TIME
    date_created_timezone = latest_status.date_created.astimezone(KYIV_TZ)
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

        if latest_status.value:
            time_diff_text = f"{langpack.MSG_TIME_SINCE_POWER_ON}\n{text_suffix}"
        elif not latest_status.value:
            time_diff_text = f"{langpack.MSG_TIME_SINCE_SHUTDOWN}\n{text_suffix}"

    final_text = f"{status_text}\n\n{datetime_text}\n{date_created_timezone:%H:%M %d\\.%m\\.%Y }\n\n{time_diff_text}"
    await update.message.reply_text(
        final_text,
        reply_markup=get_main_keyboard(langpack),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
