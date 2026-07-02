"""테스트 공통 설정.

- 프로젝트 루트를 import 경로에 추가한다.
- app 임포트 시 pydantic Settings가 요구하는 환경변수를 더미 값으로 채운다.
  (실제 MongoDB/Redis/Gemini에 접속하지 않으며, 각 테스트에서 목으로 대체한다.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
