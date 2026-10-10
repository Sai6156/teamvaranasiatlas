import json
import httpx
import pytest
from atlas import llm
from atlas.config import Settings


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    llm._cooldown.clear()
    monkeypatch.setattr(llm, "_paid_blocked_until", 0.0)
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
@pytest.mark.parametrize("status", [401, 403])
async def test_invalid_account_does_not_exhaust_routes(monkeypatch, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

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


@pytest.mark.asyncio
async def test_budget_failure_jumps_to_free_and_remembers_it(monkeypatch):
    calls = []
    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if not body["model"].endswith(":free"):
            return httpx.Response(402)
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Answer [1]"}}]}\n\ndata: [DONE]\n\n')
    original = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    events = [e async for e in llm.generate([])]
    assert [b["model"] for b in calls] == [llm.ROUTES[0][0], llm.FREE_ROUTES[0][0]]
    assert calls[-1]["provider"]["max_price"] == {"prompt": 0, "completion": 0}
    assert events[-1]["text"] == "Answer [1]"
    calls.clear()
    _ = [e async for e in llm.generate([])]
    assert [b["model"] for b in calls] == [llm.FREE_ROUTES[0][0]]
    with pytest.raises(llm.BudgetUnavailable):
        await llm.embed(["query"])
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_free_priority_on_provider_failure(monkeypatch):
    llm.mark_budget_exhausted()
    calls = []
    def handler(request):
        body = json.loads(request.content)
        calls.append(body["model"])
        if body["model"] == llm.FREE_ROUTES[0][0]:
            return httpx.Response(429)
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Answer [1]"}}]}\n\ndata: [DONE]\n\n')
    original = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    _ = [e async for e in llm.generate([])]
    assert calls == [r[0] for r in llm.FREE_ROUTES]


@pytest.mark.asyncio
async def test_embedding_budget_error_opens_free_circuit(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(lambda r: httpx.Response(402)), **kw))
    with pytest.raises(llm.BudgetUnavailable):
        await llm.embed(["query"])
    assert llm.paid_routes_blocked()
