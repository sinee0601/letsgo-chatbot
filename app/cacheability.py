import re

# 후속(맥락 의존) 신호: 이전 답변을 가리키거나 부정/비교/추가를 뜻하는 표현.
# 이런 질문은 세션 맥락 없이는 의미가 완결되지 않으므로 공유 캐시 대상에서 제외한다.
_MARKERS = [
    "말고", "대신", "빼고", "제외", "아까", "방금",
    "그거", "그건", "그것", "저거", "이거", "거기", "위에", "앞에",
    "다른", "그럼", "그러면", "추가로", "이어서", "계속",
]
_MARKER_RE = re.compile("|".join(re.escape(m) for m in _MARKERS))

# 단독 어절로 쓰일 때만 신호로 보는 짧고 모호한 표현.
_STANDALONE = {"더", "또", "그"}


def is_self_contained(message: str, has_history: bool) -> bool:
    """맥락에 의존하는 후속 질문이면 False(=공유 캐시를 조회/저장하지 않음)."""
    if not has_history:
        # 세션 첫 질문은 참조할 이전 맥락이 없으므로 항상 자기완결적이다.
        return True
    if _MARKER_RE.search(message):
        return False
    words = re.split(r"\s+", message.strip())
    if any(word in _STANDALONE for word in words):
        return False
    return True
