import asyncio
import json
import time
import httpx
from .config import settings

ROUTES = [
    (
        "z-ai/glm-5.3-flash",
        ["open-inference", "deepinfra", "relace", "streamlake", "novita"],
    ),
    (
        "deepseek/deepseek-v4.1-flash",
        ["decart", "morph", "inference-net", "sail-research", "relace"],
    ),
    ("openai/gpt-6-luna", ["openai", "azure"]),
    ("qwen/qwen3.8-flash", []),
]
BASE = "https://openrouter.ai/api/v1"
_cooldown: dict[str, float] = {}


class ModelUnavailable(Exception):
    pass


class ConfigurationError(ModelUnavailable):
    pass


def headers():
    config = settings()
    if not config.openrouter_api_key:
        raise ConfigurationError("The AI service has not been configured.")
    return {
        "Authorization": "Bearer " + config.openrouter_api_key,
        "Content-Type": "application/json",
        "HTTP-Referer": config.frontend_url,
        "X-OpenRouter-Title": "Atlas - Team Varanasi",
    }


def provider_policy(providers: list[str]):
    config = settings()
    policy = {
        "data_collection": config.openrouter_data_collection,
        "require_parameters": True,
    }
    if config.openrouter_zdr:
        policy["zdr"] = True
    if providers:
        policy.update(order=providers, only=providers, allow_fallbacks=True)
    return policy


async def embed(texts: list[str]) -> list[list[float]]:
    config = settings()
    async with httpx.AsyncClient(timeout=40) as client:
        for attempt in range(3):
            result = await client.post(
                BASE + "/embeddings",
                headers=headers(),
                json={
                    "model": config.embedding_model,
                    "input": texts,
                    "dimensions": config.embedding_dimensions,
                    "provider": {"data_collection": config.openrouter_data_collection},
                },
            )
            if result.status_code in (401, 402):
                raise ConfigurationError(
                    "The AI account key or balance needs attention."
                )
            if result.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(min(2**attempt, 4))
                continue
            if result.is_error:
                raise ModelUnavailable(
                    "Embedding service could not process this request."
                )
            data = result.json().get("data", [])
            vectors = [
                item["embedding"]
                for item in sorted(data, key=lambda item: item["index"])
            ]
            if len(vectors) != len(texts) or any(
                len(vector) != config.embedding_dimensions for vector in vectors
            ):
                raise ModelUnavailable(
                    "Embedding dimensions do not match the workspace index."
                )
            return vectors
    raise ModelUnavailable("Embedding service is busy. Please try again shortly.")


def model_payload(model: str, providers: list[str], messages: list[dict], stream: bool):
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1400,
        "stream": stream,
        "provider": provider_policy(providers),
    }
    if model.startswith("openai/"):
        payload["reasoning"] = {"effort": "low"}
        if providers == ["azure"]:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
    else:
        payload["temperature"] = 0.15
    return payload


async def generate(messages: list[dict]):
    """One provider policy per model. Never merge partial outputs across attempts."""
    deadline = time.monotonic() + 60
    attempts = [
        ROUTES[0],
        ROUTES[1],
        (ROUTES[2][0], ["openai"]),
        (ROUTES[2][0], ["azure"]),
        ROUTES[3],
    ]
    for model, providers in attempts:
        route_key = model + "/" + ",".join(providers)
        if _cooldown.get(route_key, 0) > time.monotonic():
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        emitted = False
        finished = False
        try:
            timeout = httpx.Timeout(min(18, remaining), connect=5)
            async with asyncio.timeout(remaining):
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream(
                        "POST",
                        BASE + "/chat/completions",
                        headers=headers(),
                        json=model_payload(model, providers, messages, True),
                    ) as response:
                        if response.status_code in (401, 402):
                            raise ConfigurationError(
                                "The AI account key or balance needs attention."
                            )
                        if response.status_code in (400, 422):
                            raise ConfigurationError(
                                "The AI request configuration needs attention."
                            )
                        if response.is_error:
                            _cooldown[route_key] = time.monotonic() + 30
                            continue
                        yield {"type": "model", "model": model}
                        for_line = response.aiter_lines()
                        async for line in for_line:
                            if not line.startswith("data:"):
                                continue
                            raw = line[5:].strip()
                            if raw == "[DONE]":
                                finished = True
                                break
                            try:
                                data = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            if data.get("error"):
                                raise ModelUnavailable(
                                    "The AI stream was interrupted. Regenerate your answer."
                                )
                            choices = data.get("choices", [])
                            if choices:
                                choice = choices[0]
                                if choice.get("finish_reason") == "error":
                                    raise ModelUnavailable(
                                        "The AI stream was interrupted. Regenerate your answer."
                                    )
                                if choice.get("finish_reason") == "stop":
                                    finished = True
                                if choice.get("finish_reason") == "length":
                                    raise ModelUnavailable(
                                        "The answer reached its output limit. Ask a more specific question."
                                    )
                                content = choice.get("delta", {}).get("content")
                                if content:
                                    emitted = True
                                    yield {"type": "token", "text": content}
                        if emitted:
                            if not finished:
                                raise ModelUnavailable(
                                    "The AI stream ended before the answer was complete."
                                )
                            return
                        _cooldown[route_key] = time.monotonic() + 30
        except ConfigurationError:
            raise
        except (httpx.HTTPError, TimeoutError, ModelUnavailable) as error:
            _cooldown[route_key] = time.monotonic() + 30
            if emitted:
                raise ModelUnavailable(
                    "The AI stream was interrupted. Regenerate your answer."
                ) from error
            continue
    raise ModelUnavailable(
        "All preferred AI routes are temporarily unavailable. Please try again shortly."
    )
