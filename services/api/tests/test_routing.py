import json
import httpx
import pytest
from atlas import llm
from atlas.config import Settings


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    llm._cooldown.clear()
    monkeypatch.setattr(
        llm, "settings", lambda: Settings(openrouter_api_key="test-key", _env_file=None)
    )


@pytest.mark.asyncio
async def test_fallback_keeps_model_provider_boundaries(monkeypatch):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        if body["model"] != "qwen/qwen3.8-flash":
            return httpx.Response(503)
        return httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"Supported answer [1]"}}]}\n\ndata: [DONE]\n\n',
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    events = [
        event async for event in llm.generate([{"role": "user", "content": "Question"}])
    ]
    assert [body["model"] for body in seen] == [
        "z-ai/glm-5.3-flash",
        "deepseek/deepseek-v4.1-flash",
        "openai/gpt-6-luna",
        "openai/gpt-6-luna",
        "qwen/qwen3.8-flash",
    ]
    assert seen[0]["provider"]["only"] == llm.ROUTES[0][1]
    assert seen[1]["provider"]["order"] == llm.ROUTES[1][1]
    assert seen[2]["provider"]["only"] == ["openai"]
    assert seen[3]["provider"]["only"] == ["azure"]
    assert "max_completion_tokens" in seen[3]
    assert "only" not in seen[4]["provider"]
    assert events[-1]["text"] == "Supported answer [1]"


@pytest.mark.asyncio
async def test_invalid_account_does_not_exhaust_routes(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(402)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises(llm.ConfigurationError):
        _ = [event async for event in llm.generate([])]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_partial_answer_never_gets_joined_to_fallback(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, text='data: {"choices":[{"delta":{"content":"Incomplete"}}]}\n\n'
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises(llm.ModelUnavailable):
        _ = [event async for event in llm.generate([])]
    assert len(calls) == 1


def test_headers_can_be_encoded_by_http_transport():
    assert all(value.encode("ascii") for value in llm.headers().values())
