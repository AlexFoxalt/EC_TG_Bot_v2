from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.logger.main import logger
from src.utils import _require_env


MAINTENANCE_MESSAGE = "⚠️ БОТ НЕДОСТУПЕН ⚠️\n\nУстанавливается техническое обновление ♻️\n\nВозвращайтесь позже."


async def handle_maintenance_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(MAINTENANCE_MESSAGE)


async def handle_maintenance_callback(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    try:
        await query.edit_message_text(MAINTENANCE_MESSAGE)
    except Exception:
        if query.message is not None:
            await query.message.reply_text(MAINTENANCE_MESSAGE)


def start_maintenance_bot() -> None:
    logger.bind(username="system").info("Starting maintenance bot...")
    token = _require_env("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", handle_maintenance_message))
    app.add_handler(CallbackQueryHandler(handle_maintenance_callback))
    app.add_handler(MessageHandler(filters.ALL, handle_maintenance_message))

    logger.bind(username="system").info("Maintenance bot is running...")
    app.run_polling()


if __name__ == "__main__":
    start_maintenance_bot()
