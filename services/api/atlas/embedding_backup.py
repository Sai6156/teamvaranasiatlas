"""Independent Liquid embedding space, with full-text fallback on provider failure."""
import asyncio
import math
import time
from functools import lru_cache
from pathlib import Path

import httpx
from tokenizers import Tokenizer

from .config import settings
from .llm import BASE, ModelUnavailable, headers

MODEL = "liquid/lfm-2.5-embedding-350m:free"
DIMENSIONS = 1024
_unavailable_until = 0.0


@lru_cache(maxsize=1)
def tokenizer():
    codec = Tokenizer.from_file(str(Path(__file__).parent / "assets/liquid-tokenizer.json"))
    codec.no_truncation()
    codec.no_padding()
    return codec


def segments(text: str, purpose: str):
    prefix = "query: " if purpose == "query" else "document: "
    codec = tokenizer()
    ids = codec.encode(text, add_special_tokens=False).ids
    if not ids:
        return [prefix + " "]
    # Leave room for asymmetric prefixes and the provider's special tokens.
    result = []
    for start in range(0, len(ids), 440):
        body = codec.decode(ids[start:start + 480], skip_special_tokens=False)
        value = prefix + body
        while len(codec.encode(value).ids) > 510:
            body = body[:-1]
            value = prefix + body
        result.append(value)
        if start + 480 >= len(ids):
            break
    return result


async def request_vectors(inputs: list[str], client=None):
    global _unavailable_until
    config = settings()
    if not config.free_embedding_enabled or not config.openrouter_free_api_key:
        raise ModelUnavailable("Free semantic search is not configured.")
    if _unavailable_until > time.monotonic():
        raise ModelUnavailable("Free semantic search is temporarily busy.")
    policy = {"data_collection": config.free_embedding_data_collection,
              "max_price": {"prompt": 0, "completion": 0}}
    if client is None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=4), transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as owned:
            return await request_vectors(inputs, owned)
    try:
        response = await client.post(BASE + "/embeddings", headers=headers(MODEL),
                                     json={"model": MODEL, "input": inputs, "provider": policy})
        if response.is_error:
            raise ModelUnavailable("Free semantic search is temporarily unavailable.")
        data = sorted(response.json().get("data", []), key=lambda value: value["index"])
        vectors = [item["embedding"] for item in data]
        if len(vectors) != len(inputs) or any(len(v) != DIMENSIONS or not all(math.isfinite(x) for x in v) or not any(v) for v in vectors):
            raise ModelUnavailable("Free embedding response does not match its index.")
        return vectors
    except (httpx.HTTPError, ValueError, KeyError, ModelUnavailable) as error:
        _unavailable_until = time.monotonic() + 30
        raise ModelUnavailable("Free semantic search is temporarily unavailable.") from error


async def query_vectors(queries: list[str]):
    inputs, owners = [], []
    for index, query in enumerate(queries):
        parts = segments(query, "query")
        inputs.extend(parts)
        owners.extend([index] * len(parts))
    vectors = []
    for start in range(0, len(inputs), 64):
        vectors.extend(await request_vectors(inputs[start:start + 64]))
    output = []
    for index in range(len(queries)):
        selected = [v for owner, v in zip(owners, vectors) if owner == index]
        mean = [sum(v[i] for v in selected) / len(selected) for i in range(DIMENSIONS)]
        norm = math.sqrt(sum(x * x for x in mean))
        if not norm:
            raise ModelUnavailable("Free query embedding is empty.")
        output.append([x / norm for x in mean])
    return output


async def index_chunks(db, chunks: list[dict], client=None):
    """Store segments separately, then atomically mark each complete source chunk."""
    pending, completed = [], []
    for chunk in chunks:
        parts = segments(chunk["content"], "document")
        completed.append({"id": chunk["id"], "segments": len(parts)})
        for ordinal, text in enumerate(parts):
            pending.append((chunk, ordinal, text))
    for start in range(0, len(pending), 128):
        batch = pending[start:start + 128]
        vectors = await request_vectors([text for _, _, text in batch], client)
        await db.insert("chunk_free_embeddings", [
            {"chunk_id": chunk["id"], "organization_id": chunk["organization_id"],
             "document_id": chunk["document_id"], "segment": ordinal,
             "model": MODEL, "embedding": vector}
            for (chunk, ordinal, _), vector in zip(batch, vectors)
        ], upsert=True)
    await db.rpc("finish_liquid_index", {"indexed_chunks": completed})
    return len(pending)


async def backfill_loop(db):
    while True:
        try:
            if settings().free_embedding_enabled:
                rows = await db.rpc("missing_liquid_chunks", {"batch_limit": 16})
                if rows:
                    await index_chunks(db, rows)
                    await asyncio.sleep(1)
                    continue
        except Exception:
            # Keep ingestion and chat alive while the optional provider recovers.
            pass
        await asyncio.sleep(30)
