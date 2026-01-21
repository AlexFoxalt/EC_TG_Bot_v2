from datetime import datetime

from sqlalchemy import select, desc
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
)

from src.bot.constants import KYIV_TZ, SECS_IN_MINUTE, MINS_IN_HOUR
from src.bot.keyboards import get_main_keyboard
from src.bot.lang_pack.base import BaseLangPack
from src.bot.utils import get_username_from_update, is_generator_on
from src.db.models import Status
from src.enums import Label
from src.logger.main import logger


async def handle_gen_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        logger.bind(username="system").warning("Received generator status request but effective_user is None")
        return
    username = get_username_from_update(update)
    user_lang = update.effective_user.language_code
    langpack: BaseLangPack = context.application.bot_data["languages"].from_langcode(user_lang)

    session_factory = context.application.bot_data["session_factory"]
    if session_factory is None:
        logger.bind(username="system").error("Session factory not initialized in handle_get_status")
        await update.message.reply_text(langpack.ERR_BOT_NOT_INITIALIZED)
        return

    logger.bind(username=username).info("User requested generator status")

    async with session_factory() as session:
        # Get latest status ordered by date_created DESC
        power_label = str(Label.power)
        result = await session.execute(
            select(Status).where(Status.label == power_label).order_by(desc(Status.date_created)).limit(1)
        )
        latest_status = result.scalar_one_or_none()

        if latest_status and latest_status.value:
            await update.message.reply_text(
                langpack.MSG_GEN_NOT_REQUIRED,
                reply_markup=get_main_keyboard(langpack),
            )
            return

    curr_time = datetime.now(KYIV_TZ)
    gen_status, next_switch_td = is_generator_on(curr_time.hour, curr_time.minute)

    next_switch_mins = next_switch_td.seconds // SECS_IN_MINUTE
    if next_switch_mins > MINS_IN_HOUR:
        # Convert minutes to hours if it's possible.
        # "100500 mins elapsed" message looks weird.
        next_switch_hours = next_switch_mins // MINS_IN_HOUR
        next_switch_mins = next_switch_mins % MINS_IN_HOUR

        if next_switch_mins == 0:
            next_switch_sub_text = f"{next_switch_hours} {langpack.WORD_HOURS}\\."
        else:
            next_switch_sub_text = f"{next_switch_hours} {langpack.WORD_HOURS}\\. {langpack.WORD_AND} {next_switch_mins} {langpack.WORD_MINUTES}\\."
    else:
        next_switch_sub_text = f"{next_switch_mins} {langpack.WORD_MINUTES}\\."

    if gen_status:
        message_text = langpack.MSG_GEN_ON
        next_switch_text = f"{langpack.MSG_GEN_TIME_TILL_OFF} {next_switch_sub_text}"
    else:
        message_text = langpack.MSG_GEN_OFF
        next_switch_text = f"{langpack.MSG_GEN_TIME_TILL_ON} {next_switch_sub_text}"

    await update.message.reply_text(
        f"{message_text}\n{next_switch_text}\n\n{langpack.MSG_GEN_FOOTER}",
        reply_markup=get_main_keyboard(langpack),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
