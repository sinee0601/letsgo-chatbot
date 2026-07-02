import re

_MARKERS = [
    "말고", "대신", "빼고", "제외", "아까", "방금",
    "그거", "그건", "그것", "저거", "이거", "거기", "위에", "앞에",
    "다른", "그럼", "그러면", "추가로", "이어서", "계속",
]
_MARKER_RE = re.compile("|".join(re.escape(m) for m in _MARKERS))

_STANDALONE = {"더", "또", "그"}


def is_self_contained(message: str, has_history: bool) -> bool:
    if not has_history:
        return True
    if _MARKER_RE.search(message):
        return False
    words = re.split(r"\s+", message.strip())
    if any(word in _STANDALONE for word in words):
        return False
    return True
