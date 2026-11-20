import asyncio
import logging
import threading
from typing import AsyncGenerator

from google import genai
from google.genai import types

from app.config import settings
from app.prompts.system_prompt import get_system_prompt

logger = logging.getLogger(__name__)

# Ordered fallback chain — tried in sequence if the primary model is unavailable
_MODEL_FALLBACKS = [
    settings.LLM_MODEL,
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]

_client = genai.Client(api_key=settings.LLM_API_KEY)

_gen_config = types.GenerateContentConfig(
    system_instruction=get_system_prompt(),
    temperature=settings.LLM_TEMPERATURE,
    max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
)


def _make_chat(model_name: str, history: list[dict]):
    return _client.chats.create(
        model=model_name,
        config=_gen_config,
        history=history,
    )


async def generate_response(message: str, history: list[dict]) -> str:
    """Non-streaming response with per-model fallback."""
    last_error: Exception = RuntimeError("All model fallbacks exhausted")
    for model_name in _MODEL_FALLBACKS:
        try:
            chat = _make_chat(model_name, history)
            response = await asyncio.to_thread(chat.send_message, message)
            return response.text
        except Exception as e:
            logger.warning("Model %s failed: %s", model_name, e)
            last_error = e
    raise last_error


async def stream_response(
    message: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """Streaming response with per-model fallback — yields text chunks as they arrive."""
    last_error: Exception = RuntimeError("All model fallbacks exhausted")
    for model_name in _MODEL_FALLBACKS:
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _run(name: str = model_name) -> None:
            try:
                chat = _make_chat(name, history)
                for chunk in chat.send_message_stream(message):
                    text = getattr(chunk, "text", None)
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        threading.Thread(target=_run, daemon=True).start()

        failed = False
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                logger.warning("Model %s failed: %s", model_name, item)
                last_error = item
                failed = True
                break
            yield item

        if not failed:
            return

    raise last_error
