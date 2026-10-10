"""Upload and embed on this PC. Resumable; never queues parsing on Render."""
import asyncio
import hashlib
import json
import secrets
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings

CONFIG = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
MANIFEST = ROOT / "demo-data/prepared-manifest.json"
CACHE = ROOT / "demo/prepared/embedding-cache"
CHECKPOINT = ROOT / "demo-data/seed-status.json"


async def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest["documents"]) == 30
    admin = {"apikey": CONFIG.supabase_service_role_key}
    if not CONFIG.supabase_service_role_key.startswith("sb_secret_"):
        admin["Authorization"] = "Bearer " + CONFIG.supabase_service_role_key
    CACHE.mkdir(exist_ok=True)
    statuses = {}
    async with httpx.AsyncClient(timeout=120, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
        async def request(method, path, **kwargs):
            headers = {**admin, **kwargs.pop("headers", {})}
            for attempt in range(4):
                response = await client.request(method, CONFIG.supabase_url + path, headers=headers, **kwargs)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if response.is_error:
                    # Never include headers or credential-bearing request objects.
                    raise RuntimeError(f"{method} {path}: {response.status_code}: {response.text[:400]}")
                return response
        owner_response = await request("GET", "/auth/v1/admin/users", params={"page": 1, "per_page": 1000})
        users = owner_response.json()["users"]
        owner = next((u for u in users if u["email"] == "atlas-demo-library@example.com"), None)
        if not owner:
            owner = (await request("POST", "/auth/v1/admin/users", json={"email": "atlas-demo-library@example.com", "password": secrets.token_urlsafe(48), "email_confirm": True, "user_metadata": {"full_name": "Atlas Public Demo Library"}, "app_metadata": {"atlas_demo_seed": True}})).json()
        orgs = {}
        for company in manifest["companies"]:
            org = str(uuid5(NAMESPACE_URL, "https://atlas-varanasi.vercel.app/demo/" + company["slug"]))
            orgs[company["slug"]] = org
            existing = (await request("GET", "/rest/v1/organizations", params={"id": "eq." + org})).json()
            if not existing:
                await request("POST", "/rest/v1/organizations", json={"id": org, "name": company["name"], "created_by": owner["id"], "is_demo": True, "demo_ready": False, "demo_slug": company["slug"], "demo_region": company["region"]})
        gate = asyncio.Semaphore(2)

        async def seed_document(doc):
            async with gate:
                org = orgs[doc["company_slug"]]
                docid = str(uuid5(NAMESPACE_URL, "https://atlas-varanasi.vercel.app/demo/" + doc["company_slug"] + "/" + doc["slug"]))
                old = (await request("GET", "/rest/v1/documents", params={"id": "eq." + docid})).json()
                if old and old[0]["content_hash"] != doc["sha256"]:
                    raise RuntimeError("Source changed; version the dataset before replacing published content")
                if old and old[0]["status"] == "ready" and old[0]["chunk_count"] == doc["chunks"]:
                    statuses[docid] = {"company": doc["company_slug"], "document": doc["slug"], "ready": True, "chunks": doc["chunks"]}
                    print(json.dumps(statuses[docid]), flush=True)
                    return
                storage = f"{org}/{docid}/original"
                data = (ROOT / doc["path"]).read_bytes()
                assert hashlib.sha256(data).hexdigest() == doc["sha256"]
                await request("POST", "/storage/v1/object/company-documents/" + storage, content=data, headers={"Content-Type": doc["mime_type"], "x-upsert": "true"})
                if not old:
                    await request("POST", "/rest/v1/documents", json={"id": docid, "organization_id": org, "uploaded_by": owner["id"], "name": doc["title"] + (".pdf" if doc["pages"] else ".html"), "mime_type": doc["mime_type"], "size_bytes": doc["bytes"], "content_hash": doc["sha256"], "storage_path": storage, "collection": doc["collection"], "status": "embedding", "total_pages": doc["pages"], "processed_pages": doc["pages"], "index_total_chunks": doc["chunks"], "index_completed_chunks": 0, "indexing_version": "local-demo-v1", "extraction_note": doc["extraction_note"]})
                if "--stage-only" in sys.argv:
                    print(json.dumps({"source_uploaded": doc["company_slug"], "document": doc["slug"]}), flush=True)
                    return
                chunks = json.loads((ROOT / doc["chunk_path"]).read_text(encoding="utf-8"))
                for offset in range(0, len(chunks), 32):
                    batch = chunks[offset:offset + 32]
                    key = hashlib.sha256((CONFIG.embedding_model + json.dumps([c["text"] for c in batch], ensure_ascii=False)).encode()).hexdigest()
                    cache = CACHE / (key + ".json")
                    if cache.exists():
                        vectors = json.loads(cache.read_text())
                    else:
                        for attempt in range(4):
                            response = await client.post("https://openrouter.ai/api/v1/embeddings", headers={"Authorization": "Bearer " + CONFIG.openrouter_api_key}, json={"model": CONFIG.embedding_model, "input": [c["text"] for c in batch], "dimensions": CONFIG.embedding_dimensions, "provider": {"data_collection": CONFIG.openrouter_data_collection}})
                            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            if response.is_error:
                                raise RuntimeError(f"Embedding API returned {response.status_code}")
                            vectors = [item["embedding"] for item in sorted(response.json()["data"], key=lambda item: item["index"])]
                            break
                        assert len(vectors) == len(batch) and all(len(v) == CONFIG.embedding_dimensions for v in vectors)
                        cache.write_text(json.dumps(vectors), encoding="utf-8")
                    records = [{"id": str(uuid5(NAMESPACE_URL, docid + "/" + str(offset + n))), "organization_id": org, "document_id": docid, "ordinal": offset + n, "content": c["text"], "location": c["location"], "embedding": vector, "embedding_model": CONFIG.embedding_model} for n, (c, vector) in enumerate(zip(batch, vectors))]
                    await request("POST", "/rest/v1/chunks", json=records, headers={"Prefer": "resolution=merge-duplicates"})
                    await request("PATCH", "/rest/v1/documents", params={"id": "eq." + docid}, json={"index_completed_chunks": min(offset + len(batch), len(chunks))})
                    print(json.dumps({"indexing": doc["company_slug"], "document": doc["slug"], "completed": min(offset + len(batch), len(chunks)), "total": len(chunks)}), flush=True)
                check = await request("GET", "/rest/v1/chunks", params={"document_id": "eq." + docid, "select": "id", "limit": "1"}, headers={"Prefer": "count=exact"})
                assert int(check.headers["content-range"].split("/")[-1]) == len(chunks)
                await request("PATCH", "/rest/v1/documents", params={"id": "eq." + docid}, json={"status": "ready", "chunk_count": len(chunks), "error_message": None})
                statuses[docid] = {"company": doc["company_slug"], "document": doc["slug"], "ready": True, "chunks": len(chunks)}
                CHECKPOINT.write_text(json.dumps(statuses, indent=2), encoding="utf-8")
                print(json.dumps(statuses[docid]), flush=True)
        await asyncio.gather(*(seed_document(d) for d in manifest["documents"]))
        if "--stage-only" in sys.argv:
            print(json.dumps({"staged_sources": 30, "published": False}), flush=True)
            return
        for org in orgs.values():
            await request("POST", "/rest/v1/rpc/publish_demo_library", json={"org": org})
        print(json.dumps({"published_companies": len(orgs), "ready_documents": len(statuses), "chunks": sum(d["chunks"] for d in statuses.values())}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
