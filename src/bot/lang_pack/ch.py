from src.bot.lang_pack.base import BaseLangPack


class CHLangPack(BaseLangPack):
    BTN_POWER_STATUS = "💡 Elektřina 💡"
    BTN_GEN_STATUS = "🔋 Generátor 🔋"
    BTN_SETTINGS = "⚙️ Nastavení ⚙️"
    BTN_REPORT_ERROR = "🆘 Nahlásit chybu 🆘"

    INLINE_BTN_NIGHT_SOUND_ON = "🔊ZAPNOUT noční zvuk"
    INLINE_BTN_NIGHT_SOUND_OFF = "🔇VYPNOUT noční zvuk"
    INLINE_BTN_YES = "Ano"
    INLINE_BTN_NO = "Ne"

    MSG_USE_KEYBOARD = "Použijte klávesnici níže pro interakci s botem 👇"
    MSG_NOTIFICATIONS_ON = (
        "Skvělé! Oznámení jsou zapnutá. 🔔\n\n"
        "Chcete vypnout zvuk pro noční oznámení "
        "(oznámení, která přicházejí v noci mezi 22:00 a 08:00, budou tichá)?"
    )
    MSG_WELCOME_USER = "Vítejte, {username}!"
    MSG_Q_ENABLE_NOTIFS = (
        "Chcete zapnout oznámení (bot bude automaticky posílat zprávy do chatu, když se elektřina zapne/vypne)?"
    )
    MSG_GEN_NOT_REQUIRED = "⚡️ Elektřina je ZAPNUTÁ ⚡️\n\nGenerátor není potřeba"
    MSG_GEN_ON = "🔋 *Generátor BĚŽÍ* 🔋"
    MSG_GEN_OFF = "🪫 *Generátor NEBĚŽÍ* 🪫"
    MSG_GEN_TIME_TILL_OFF = "⏳ Podle rozvrhu do vypnutí:"
    MSG_GEN_TIME_TILL_ON = "⏳ Podle rozvrhu do spuštění:"
    MSG_GEN_SHOULD_BE_OFF = "⚠️ _Generátor běží, ale podle rozvrhu by měl být *VYPNUT*\\!_"
    MSG_GEN_SHOULD_BE_ON = "⚠️ _Generátor je vypnutý, ale podle rozvrhu by měl být *ZAPNUT*\\!_"
    MSG_POWER_STATUS_NOT_AVAILABLE = "⚠️ Informace jsou momentálně nedostupné. Zkuste to prosím později."
    MSG_POWER_IS_ON = "🟢 *Elektřina je ZAPNUTÁ\\!* 🟢"
    MSG_POWER_IS_OFF = "🔴 *Elektřina je VYPNUTÁ* 🔴"
    MSG_POWER_TURN_ON_TIME = "📅 Čas zapnutí"
    MSG_POWER_TURN_OFF_TIME = "📅 Čas vypnutí"
    MSG_REPORT_ERROR = "Pokud něco nefunguje, napište mi přímo a vše opravíme a nastavíme 🤝\n\n@AlexFoxalt"
    MSG_USER_NOT_FOUND = "Uživatel nebyl nalezen. Pro registraci použijte příkaz /start."
    MSG_NOTIFS_DISABLED = "Oznámení jsou vypnutá. Můžete to změnit později.\n\nNastavení bylo aktualizováno ✅"
    MSG_NOTIFS_DISABLED_AND_REG_FINISHED = "Oznámení jsou vypnutá. Můžete to změnit později."
    MSG_REGISTRATION_COMPLETED = "Registrace dokončena! Nyní můžete používat bota 🎉"
    MSG_NOTIF_NIGHT_SOUND = "Zvuková oznámení v noci"
    MSG_SETTINGS_UPDATED = "Nastavení bylo aktualizováno ✅"
    MSG_TIME_SINCE_SHUTDOWN = "⏳ Čas od vypnutí"
    MSG_TIME_SINCE_POWER_ON = "⏳ Čas od zapnutí"

    NOTIF_ATTENTION = "📢️  *POZOR*  📢"
    NOTIF_POWER_TURN_ON_TIME = "⏳Elektřina byla zapnutá"
    NOTIF_POWER_TURN_OFF_TIME = "⏳Elektřina byla vypnutá"
    NOTIF_POWER_SURGE_WARN = "⚠️ Mohlo to být způsobeno přepětím v síti\\."
    NOTIF_FOOTER = (
        "_Tuto zprávu jste dostali, protože jste v nastavení bota zapnuli oznámení\\. Můžete je kdykoli vypnout\\._"
    )

    WORD_MINUTES = "min"
    WORD_HOURS = "h"
    WORD_AND = "a"
    WORD_USER = "Uživatel"
    WORD_POWER = "Elektřina je"
    WORD_ENABLED_LOWER = "zapnuto"
    WORD_DISABLED_LOWER = "vypnuto"

    ERR_BOT_NOT_INITIALIZED = "Bot nebyl správně inicializován. Kontaktujte prosím administrátora."
    ERR_USER_NOT_FOUND = "Uživatel nebyl nalezen. Použijte znovu příkaz /start."
    ERR_SESSION_EXPIRED = "Relace vypršela. Použijte znovu příkaz /start."

    def __repr__(self) -> str:
        return "CH"
