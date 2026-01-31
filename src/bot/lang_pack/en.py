from src.bot.lang_pack.base import BaseLangPack


class ENLangPack(BaseLangPack):
    BTN_POWER_STATUS = "💡 Power 💡"
    BTN_GEN_STATUS = "🔋 Generator 🔋"
    BTN_SETTINGS = "⚙️ Settings ⚙️"
    BTN_REPORT_ERROR = "🆘 Report an error 🆘"

    INLINE_BTN_NIGHT_SOUND_ON = "🔊TURN ON night sound"
    INLINE_BTN_NIGHT_SOUND_OFF = "🔇TURN OFF night sound"
    INLINE_BTN_YES = "Yes"
    INLINE_BTN_NO = "No"

    MSG_USE_KEYBOARD = "Use the keyboard below to interact with the bot 👇"
    MSG_NOTIFICATIONS_ON = (
        "Great! Notifications are enabled. 🔔\n\n"
        "Would you like to turn off the sound for night notifications "
        "(notifications that arrive at night between 22:00 and 08:00 will be silent)?"
    )
    MSG_WELCOME_USER = "Welcome, {username}!"
    MSG_Q_ENABLE_NOTIFS = "Would you like to enable notifications (the bot will automatically send messages to the chat when the power is turned on/off)?"
    MSG_GEN_NOT_REQUIRED = "⚡️ Power is ON ⚡️\n\nGenerator not required"
    MSG_GEN_ON = "🔋 *Generator is RUNNING* 🔋"
    MSG_GEN_OFF = "🪫 *Generator is NOT RUNNING* 🪫"
    MSG_GEN_TIME_TILL_OFF = "⏳ According to schedule, until shutdown:"
    MSG_GEN_TIME_TILL_ON = "⏳ According to schedule, until startup:"
    MSG_GEN_SHOULD_BE_OFF = "⚠️ _The generator is running, but according to the schedule, it should be turned *OFF*\\!_"
    MSG_GEN_SHOULD_BE_ON = "⚠️ _The generator is turned off, but according to the schedule, it should be turned *ON*\\!_"
    MSG_POWER_STATUS_NOT_AVAILABLE = "⚠️ Information is currently unavailable. Please try again later."
    MSG_POWER_IS_ON = "🟢 *Power is ON\\!* 🟢"
    MSG_POWER_IS_OFF = "🔴 *Power is OFF* 🔴"
    MSG_POWER_TURN_ON_TIME = "📅 Turn\\-on time"
    MSG_POWER_TURN_OFF_TIME = "📅 Turn\\-off time"
    MSG_REPORT_ERROR = "If something is not working, please message me directly and we will fix and set everything up 🤝\n\n@AlexFoxalt"
    MSG_USER_NOT_FOUND = "User not found. Please use the /start command to register."
    MSG_NOTIFS_DISABLED = "Notifications are disabled. You can change this later.\n\nSettings updated ✅"
    MSG_NOTIFS_DISABLED_AND_REG_FINISHED = "Notifications are disabled. You can change this later."
    MSG_REGISTRATION_COMPLETED = "Registration completed! You can now use the bot 🎉"
    MSG_NOTIF_NIGHT_SOUND = "Sound notifications at night"
    MSG_SETTINGS_UPDATED = "Settings updated ✅"
    MSG_TIME_SINCE_SHUTDOWN = "⏳ Time since shutdown"
    MSG_TIME_SINCE_POWER_ON = "⏳ Time since power\\-on"

    NOTIF_ATTENTION = "📢️  *ATTENTION*  📢"
    NOTIF_POWER_TURN_ON_TIME = "⏳Power was on for"
    NOTIF_POWER_TURN_OFF_TIME = "⏳Power was off for"
    NOTIF_POWER_SURGE_WARN = "⚠️ It could be caused by a power surge\\."
    NOTIF_FOOTER = "_You received this message because you enabled notifications in the bot settings\\. You can disable them at any time\\._"

    WORD_MINUTES = "min"
    WORD_HOURS = "h"
    WORD_AND = "and"
    WORD_USER = "User"
    WORD_POWER = "Power is"
    WORD_ENABLED_LOWER = "enabled"
    WORD_DISABLED_LOWER = "disabled"

    ERR_BOT_NOT_INITIALIZED = "The bot was not initialized correctly. Please contact the administrator."
    ERR_USER_NOT_FOUND = "User not found. Please use the /start command again."
    ERR_SESSION_EXPIRED = "The session has expired. Please use the /start command again."

    def __repr__(self) -> str:
        return "EN"
