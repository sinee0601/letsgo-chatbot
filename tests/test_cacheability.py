"""분류 레이어: is_self_contained 휴리스틱."""
import pytest

from app.cacheability import is_self_contained


@pytest.mark.parametrize(
    "message,has_history,expected",
    [
        # 세션 첫 질문은 참조할 맥락이 없으므로 항상 자기완결적.
        ("부산 맛집 추천", False, True),
        ("아까 거 말고 다른 데", False, True),  # 첫 턴이면 신호가 있어도 True
        # 이어지는 대화에서 독립적 질문 → 캐시 대상.
        ("서울 날씨 어때", True, True),
        ("제주도 3박 4일 코스", True, True),
        # 이어지는 대화에서 맥락 의존(후속) 질문 → 캐시 제외.
        ("아까 거 말고 다른 데", True, False),
        ("그거 다시 알려줘", True, False),
        ("대신 부산으로 바꿔줘", True, False),
        ("거기 근처 카페는?", True, False),
    ],
)
def test_is_self_contained(message, has_history, expected):
    assert is_self_contained(message, has_history) is expected


def test_standalone_marker_only_matches_whole_word():
    # '더'가 단독 어절이면 후속 신호로 본다.
    assert is_self_contained("더 저렴한 곳", True) is False
    # '더'가 다른 단어의 일부이면 신호가 아니다.
    assert is_self_contained("더위 피할 여행지", True) is True
