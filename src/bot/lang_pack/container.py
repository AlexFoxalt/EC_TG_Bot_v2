from src.bot.lang_pack.base import BaseLangPack
from src.bot.lang_pack.en import ENLangPack
from src.bot.lang_pack.ru import RULangPack
from src.bot.lang_pack.uk import UKLangPack


class LangContainer:
    uk = UKLangPack()
    ru = RULangPack()
    en = ENLangPack()

    _default = ru
    _langcode_to_object_map = {"uk": uk, "ru": ru, "en": en}
    _langcodes_as_list = list(_langcode_to_object_map.values())
    _curr_i = 0

    def from_langcode(self, lang_code: str) -> BaseLangPack:
        return self._langcode_to_object_map.get(lang_code.lower(), self._default)

    def __iter__(self):
        return self

    def __next__(self):
        if self._curr_i == len(self._langcodes_as_list):
            self._curr_i = 0
            raise StopIteration
        val = self._langcodes_as_list[self._curr_i]
        self._curr_i += 1
        return val
