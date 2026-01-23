from src.bot.lang_pack.base import BaseLangPack
from src.bot.lang_pack.en import ENLangPack
from src.bot.lang_pack.ru import RULangPack
from src.bot.lang_pack.uk import UKLangPack


class LangContainer:
    def __init__(self) -> None:
        self.uk = UKLangPack()
        self.ru = RULangPack()
        self.en = ENLangPack()
        self._default = self.ru
        self._langcode_to_langpack = {"uk": self.uk, "ru": self.ru, "en": self.en}
        self._langpacks_list = list(self._langcode_to_langpack.values())
        self._curr_i = 0

    def from_langcode(self, lang_code: str) -> BaseLangPack:
        if not lang_code:
            return self._default
        return self._langcode_to_langpack.get(lang_code.lower(), self._default)

    def __iter__(self):
        self._curr_i = 0
        return self

    def __next__(self):
        if self._curr_i >= len(self._langpacks_list):
            raise StopIteration
        val = self._langpacks_list[self._curr_i]
        self._curr_i += 1
        return val
