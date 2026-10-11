"""Build the separate Liquid index for ready documents without modifying OpenAI vectors."""
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
os.chdir(ROOT / "services/api")
from atlas.config import settings
from atlas.db import Database
from atlas.embedding_backup import index_chunks
from atlas.llm import ModelUnavailable


class BackfillDatabase(Database):
    def __init__(self, client):
        super().__init__(privileged=True)
        self.client = client

    async def request(self, method, path, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        response = await self.client.request(method, self.base + path, headers=headers, **kwargs)
        if response.is_error:
            raise RuntimeError(f"Database backfill request failed ({response.status_code})")
        return response


async def main():
    if not settings().free_embedding_enabled:
        raise SystemExit("Enable FREE_EMBEDDING_ENABLED after accepting the provider data policy.")
    async with httpx.AsyncClient(timeout=90, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
        db = BackfillDatabase(client)
        documents = await db.select("documents", status="eq.ready", select="id", limit="1000")
        if not documents:
            return
        chunks, cursor = [], None
        while True:
            filters = {"select": "id,organization_id,document_id,content", "free_embedding_ready": "eq.false",
                       "document_id": "in.(" + ",".join(d["id"] for d in documents) + ")", "order": "id.asc", "limit": "1000"}
            if cursor:
                filters["id"] = "gt." + cursor
            page = await db.select("chunks", **filters)
            chunks.extend(page)
            if len(page) < 1000:
                break
            cursor = page[-1]["id"]
        print(json.dumps({"pending_chunks": len(chunks)}), flush=True)
        gate, completed = asyncio.Semaphore(3), 0

        async def batch(rows):
            nonlocal completed
            async with gate:
                for attempt in range(4):
                    try:
                        await index_chunks(db, rows, client)
                        completed += len(rows)
                        print(json.dumps({"indexed_chunks": completed, "total_chunks": len(chunks)}), flush=True)
                        return
                    except ModelUnavailable:
                        if attempt == 3:
                            raise
                        await asyncio.sleep(31)

        await asyncio.gather(*(batch(chunks[start:start + 64]) for start in range(0, len(chunks), 64)))
        print(json.dumps({"backfill_complete": True, "indexed_chunks": completed}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
