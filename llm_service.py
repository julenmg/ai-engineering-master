import time
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from config import Settings
from context import SYSTEM_PROMPT


async def generate_estimation(
    transcription: str,
    settings: Settings,
    model_override: str | None = None,
) -> dict:
    model = model_override or settings.llm_model
    user_message = f"Transcripción de la reunión:\n\n{transcription}"
    t0 = time.monotonic()

    if settings.llm_provider == "anthropic":
        result = await _call_anthropic(SYSTEM_PROMPT, user_message, model, settings.anthropic_api_key)
    else:
        result = await _call_openai(SYSTEM_PROMPT, user_message, model, settings.openai_api_key)

    result["latency_ms"] = int((time.monotonic() - t0) * 1000)
    return result


async def _call_openai(system: str, user: str, model: str, api_key: str) -> dict:
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return {
        "estimation": resp.choices[0].message.content,
        "model": resp.model,
        "provider": "openai",
        "usage": {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
        },
    }


async def _call_anthropic(system: str, user: str, model: str, api_key: str) -> dict:
    client = AsyncAnthropic(api_key=api_key)
    resp = await client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return {
        "estimation": resp.content[0].text,
        "model": resp.model,
        "provider": "anthropic",
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        },
    }
