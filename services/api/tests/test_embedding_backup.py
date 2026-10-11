import json
from types import SimpleNamespace

import httpx
import pytest

from atlas import embedding_backup as backup, llm, retrieval, worker
from atlas.config import Settings
from atlas.extraction import Block


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    config = Settings(openrouter_api_key="paid-key", openrouter_free_api_key="free-key",
                      free_embedding_enabled=True, free_embedding_data_collection="allow", _env_file=None)
    for module in (backup, llm, retrieval, worker):
        monkeypatch.setattr(module, "settings", lambda: config)
    monkeypatch.setattr(backup, "_unavailable_until", 0.0)


def test_long_passages_preserve_tail_and_fit_token_limit():
    text = ("Company policy information with dates and figures. " * 500) + "FINAL_UNIQUE_MARKER"
    parts = backup.segments(text, "document")
    assert len(parts) > 1
    assert all(part.startswith("document: ") and len(backup.tokenizer().encode(part).ids) <= 510 for part in parts)
    assert "FINAL_UNIQUE_MARKER" in parts[-1]


@pytest.mark.asyncio
async def test_free_vectors_use_only_second_key_and_zero_price(monkeypatch):
    seen = []
    def handler(request):
        seen.append(request)
        body = json.loads(request.content)
        return httpx.Response(200, json={"data": [{"index": i, "embedding": [0.1] * 1024} for i in range(len(body["input"]))]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        vectors = await backup.request_vectors(["query: policy"], client)
    assert len(vectors[0]) == 1024
    assert seen[0].headers["authorization"] == "Bearer free-key"
    assert json.loads(seen[0].content)["provider"]["max_price"] == {"prompt": 0, "completion": 0}


@pytest.mark.asyncio
async def test_dimension_mismatch_cannot_enter_liquid_index():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1] * 1536}]}))) as client:
        with pytest.raises(llm.ModelUnavailable):
            await backup.request_vectors(["query: policy"], client)


@pytest.mark.asyncio
async def test_credit_failure_searches_only_matching_free_space(monkeypatch):
    async def paid(_):
        raise llm.BudgetUnavailable("No paid budget")
    async def free(queries):
        return [[0.1] * 1024 for _ in queries]
    monkeypatch.setattr(retrieval, "embed", paid)
    monkeypatch.setattr(retrieval, "query_vectors", free)
    calls = []
    class DB:
        async def rpc(self, name, body):
            calls.append((name, body))
            return []
    await retrieval.retrieve(DB(), "test-organization", "What is the policy?")
    assert all(name == "search_chunks_liquid" for name, _ in calls)
    assert all(body["org"] == "test-organization" and len(body["query_embedding"]) == 1024 for _, body in calls)


@pytest.mark.asyncio
async def test_new_upload_publishes_when_paid_embedding_is_exhausted(monkeypatch):
    async def paid(_):
        raise llm.BudgetUnavailable("No paid budget")
    async def prepare(*args, **kwargs):
        return [Block("Company policy requires approval.", {"kind": "lines", "label": "Line 1"})], "Text extracted"
    captured = []
    async def index(db, chunks):
        captured.extend(chunks)
    monkeypatch.setattr(worker, "embed", paid)
    monkeypatch.setattr(worker, "prepare", prepare)
    monkeypatch.setattr(worker, "index_chunks", index)
    doc = {"id": "document", "organization_id": "organization", "name": "policy.txt", "storage_path": "policy.txt", "status": "queued"}
    class DB:
        published = False
        async def select(self, *args, **kwargs): return [doc]
        async def request(self, *args, **kwargs): return SimpleNamespace(content=b"Company policy")
        async def update(self, *args, **kwargs): return [doc]
        async def delete(self, *args, **kwargs): return None
        async def insert(self, table, rows, **kwargs): return [{**row, "id": "chunk"} for row in rows]
        async def rpc(self, name, body): self.published = True; return True
    db = DB()
    await worker.process(db, {"id": "job", "document_id": "document", "organization_id": "organization", "kind": "ingest", "attempts": 1})
    assert db.published and len(captured) == 1
    assert captured[0]["embedding"] is None


def test_compact_storage_keeps_exact_float32_values():
    import struct
    original = [0.10000000014901, -0.0344679687733984, 1.0e-7, 0.123456789, 0.0]
    converted = backup.storage_vector(original)
    assert [struct.pack("!f", value) for value in converted] == [struct.pack("!f", value) for value in original]
