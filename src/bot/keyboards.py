from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.lang_pack.base import BaseLangPack


def get_main_keyboard(langpack: BaseLangPack) -> ReplyKeyboardMarkup:
    """Get the main persistent keyboard for registered users."""
    keyboard = [
        [KeyboardButton(langpack.BTN_POWER_STATUS, api_kwargs={"style": "success"})],
        [KeyboardButton(langpack.BTN_GEN_STATUS, api_kwargs={"style": "success"})],
        [
            KeyboardButton(langpack.BTN_SETTINGS),
            KeyboardButton(langpack.BTN_REPORT_ERROR, api_kwargs={"style": "danger"}),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)


def get_night_sound_choice_keyboard(langpack: BaseLangPack) -> InlineKeyboardMarkup:
    """Get inline keyboard for night sound preference choice."""
    keyboard = [
        [
            InlineKeyboardButton(langpack.INLINE_BTN_NIGHT_SOUND_ON, callback_data="night_sound_yes"),
            InlineKeyboardButton(langpack.INLINE_BTN_NIGHT_SOUND_OFF, callback_data="night_sound_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_choice_keyboard(langpack: BaseLangPack) -> InlineKeyboardMarkup:
    """Get inline keyboard for notification preference choice."""
    keyboard = [
        [
            InlineKeyboardButton(langpack.INLINE_BTN_YES, callback_data="notif_yes"),
            InlineKeyboardButton(langpack.INLINE_BTN_NO, callback_data="notif_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
