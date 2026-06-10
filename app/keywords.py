import re

from kiwipiepy import Kiwi

kiwi = Kiwi()

_ALLOWED_TAGS = {"NNG", "NNP", "SL", "SN", "IC"}

_STOPWORDS = {"추천", "정보", "소개", "곳", "장소", "여행", "관광", "관광지", "여기", "거기"}

_KEEP = re.compile(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ\s]")


def _base_tag(tag: str) -> str:
    return tag.split("-")[0]


def _normalize_raw(text: str) -> str:
    return " ".join(_KEEP.sub(" ", text.lower()).split())[:100]


def extract_keywords(user_message: str) -> str:
    tokens = kiwi.tokenize(user_message)

    keywords = {
        t.form
        for t in tokens
        if _base_tag(t.tag) in _ALLOWED_TAGS and t.form and t.form not in _STOPWORDS
    }
    result = " ".join(sorted(keywords))[:100]

    return result or _normalize_raw(user_message)
