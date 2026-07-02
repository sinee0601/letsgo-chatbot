import struct

from app.config import settings
from app.gemini import client


async def embed_text(text: str) -> bytes:
    result = await client.aio.models.embed_content(
        model=settings.embedding_model,
        contents=text,
    )
    values = result.embeddings[0].values
    return struct.pack(f"<{len(values)}f", *values)
