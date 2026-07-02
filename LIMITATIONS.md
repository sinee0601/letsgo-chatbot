# LetsGO Chatbot — 한계점 분석 (Limitations)

> 작성일: 2026-07-02
> 대상 커밋: `5170642` (main)
> 범위: `app/` 백엔드 (FastAPI + Gemini + MongoDB + Redis)

## 프로젝트 개요

LetsGO는 여행 도메인 챗봇 백엔드로, 다음 흐름으로 동작한다.

```
사용자 메시지
  → Kiwi 형태소 분석으로 키워드 추출 (keywords.py)
  → Redis 키워드 캐시 조회 (repository.py)
  → 캐시 미스 시 세션 히스토리 주입 + Gemini 호출 (gemini.py)
  → MongoDB에 대화 로그 저장 (repository.py)
```

계층은 `router` → `gemini` / `repository` / `keywords`로 분리되어 있고 구조는 깔끔하나,
정확성·보안·확장성 측면에서 아래와 같은 한계가 있다.

---

## 1. 캐싱 로직의 정확성 문제 (심각도: 높음)

**위치:** `app/router.py:23-42`, `app/repository.py:83-94`

키워드 기반 캐싱이 **세션 컨텍스트를 무시**한다.

- 캐시 키가 `extract_keywords(message)`로만 생성되어(`repository.py:83`),
  키워드가 겹치면 **다른 세션·다른 대화 맥락이어도 동일한 답변**이 반환된다.
- 예: "부산 맛집" 질문의 답변이 캐시되면, "부산 맛집 말고 다른 데"처럼
  의도가 정반대인 질문도 불용어 제거 후 키워드가 겹쳐 캐시된 답변을 받을 수 있다.
- 캐시 히트 시 히스토리를 전혀 참조하지 않으므로(`router.py:26-28`), 멀티턴 대화의 일관성이 깨진다.
- `if keywords` 가드로 빈 키워드는 캐시를 건너뛰지만, `extract_keywords`에 `_normalize_raw` 폴백이 있어
  사실상 거의 빈 값이 나오지 않아 가드가 무력하다.

**개선 방향:** 캐시 키에 세션/맥락 요소를 반영하거나, 멀티턴 대화에는 캐시를 적용하지 않는다.

## 2. 예외 처리가 과도하게 뭉뚱그려짐 (심각도: 높음)

**위치:** `app/router.py:37-38`

```python
try:
    bot_response = await generate_response(request.message, history)
except:
    raise HTTPException(status_code=429, detail="gemini 서버에러")
```

- bare `except:`로 **모든 예외를 무조건 429(Too Many Requests)** 로 변환한다.
  인증 오류, 네트워크 오류, 잘못된 프롬프트, 코드 버그가 전부 같은 메시지로 묻혀 디버깅이 불가능하다.
- `KeyboardInterrupt`, `SystemExit` 같은 시스템 예외까지 삼킨다.
- 프로젝트 전체에 **로깅이 전혀 없다.**

**개선 방향:** 최소 `except Exception`으로 좁히고, 예외 유형별 상태코드 분기 + 구조화 로깅을 추가한다.

## 3. 세션 히스토리 관리의 한계 (심각도: 높음)

**위치:** `app/repository.py:33-39`

```python
cursor = (
    chat_logs_collection.find({"session_id": session_id})
    .sort("created_at", 1)   # 오름차순 → 가장 오래된 것부터
    .limit(limit)            # limit=20
)
```

- **가장 오래된 20개**만 조회한다. 대화가 20턴을 넘으면 최신 대화가 아니라
  **초기 대화만** 히스토리로 주입되어 최근 맥락이 유실된다.
  (최신 N개를 역순 조회 후 다시 시간순으로 재정렬해야 함)
- 히스토리 **개수만 제한하고 토큰 길이 제한이 없어**, 긴 답변이 누적되면
  Gemini 컨텍스트 한도 초과 위험이 있다.

## 4. 보안 / 운영 설정 (심각도: 높음)

**위치:** `app/main.py:23-29`, `app/router.py` 전반

- CORS `allow_origins=["*"]` — 개발용으로는 무방하나 운영 배포 시 그대로면 위험.
- **인증·인가·레이트리밋이 전혀 없다.**
  - `session_id`만 알면 누구나 남의 세션 로그를 조회·삭제할 수 있다 (`GET/DELETE /chat/...`).
  - Gemini API를 무제한 호출시켜 **비용 폭탄**을 유발할 수 있다.
- 프롬프트 인젝션 방어(입력 필터링, system_instruction 보호)가 없다.

## 5. 데이터 / 타임존 / 스키마 (심각도: 중간)

- `app/repository.py:26` — `datetime.utcnow()`는 **deprecated**(Python 3.12+)이며 timezone-naive.
  `datetime.now(timezone.utc)` 권장.
- `app/gemini.py:28` — `response.text`가 `None`일 수 있다(안전 필터 차단, 빈 응답).
  그대로 저장/반환하면 스키마 검증(`bot_response: str`)에서 500 에러가 발생한다.
- `app/database.py:14-15` — MongoDB 인덱스가 단일 필드뿐.
  목록·페이지네이션 조회에는 `session_id + created_at` 복합 인덱스가 유리하다.

## 6. 확장성 / 기능 (심각도: 중간)

- **스트리밍 미지원:** 응답을 통째로 기다린 뒤 반환하므로 체감 지연이 크다.
  챗봇 UX상 SSE/스트리밍이 사실상 필수.
- **RAG·실제 여행 데이터 연동 없음:** 순수 Gemini 생성에만 의존해
  최신 정보·정확한 장소 정보에 대한 환각(hallucination) 위험이 크다.
  여행 챗봇의 핵심 가치인 실데이터 근거가 빠져 있다.
- 캐시 무효화 전략이 TTL(24h)뿐이라 원본 데이터가 바뀌어도 갱신 수단이 없다.

## 7. 테스트 / 품질 (심각도: 중간)

- **테스트 코드가 전무하다** (`tests/` 없음).
- CI, 린터(ruff/flake8), 타입체크(mypy) 설정이 없다.
- `.env` 필수값은 pydantic이 검증하나, 설정 오류 시 앱이 시작 시점에 죽는 것 외 안내가 없다.

---

## 우선순위 요약

| 순위 | 항목 | 이유 |
|------|------|------|
| 🔴 즉시 | 캐시의 세션/컨텍스트 무시(#1), bare except(#2), 히스토리 정렬 버그(#3) | 정확성·디버깅 직결 |
| 🟠 배포 전 | 인증·레이트리밋·CORS(#4), `response.text` None 처리(#5) | 보안·비용·안정성 |
| 🟡 개선 | 스트리밍, RAG 연동(#6), 테스트·CI(#7) | UX·신뢰성·유지보수 |
