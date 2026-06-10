from google import genai
from google.genai import types

from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)
_config = types.GenerateContentConfig(system_instruction=settings.system_instruction)


async def generate_response(
    user_message: str,
    history: list[dict] | None = None,
) -> str:
    contents = []

    if history:
        for entry in history:
            contents.append({"role": "user", "parts": [{"text": entry["user_message"]}]})
            contents.append({"role": "model", "parts": [{"text": entry["bot_response"]}]})

    contents.append({"role": "user", "parts": [{"text": user_message}]})

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=_config,
    )
    return response.text
