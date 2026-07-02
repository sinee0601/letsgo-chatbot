"""임베딩 레이어: embed_text (Gemini 임베딩 호출은 목으로 대체)."""
import struct
from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.embeddings as embeddings


async def test_embed_text_packs_float32(monkeypatch):
    values = [0.1, -0.2, 0.3, 0.4]
    fake_response = SimpleNamespace(embeddings=[SimpleNamespace(values=values)])

    embed_content = AsyncMock(return_value=fake_response)
    fake_client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))
    )
    monkeypatch.setattr(embeddings, "client", fake_client)

    result = await embeddings.embed_text("부산 여행")

    # float32 4바이트 * 4개 = 16바이트
    assert isinstance(result, bytes)
    assert len(result) == len(values) * 4
    # 다시 언팩하면 원래 값과 근사 일치
    unpacked = struct.unpack(f"<{len(values)}f", result)
    for got, expected in zip(unpacked, values):
        assert got == struct.unpack("<f", struct.pack("<f", expected))[0]

    embed_content.assert_awaited_once()
    _, kwargs = embed_content.call_args
    assert kwargs["contents"] == "부산 여행"
