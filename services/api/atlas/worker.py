import asyncio
import logging
from datetime import datetime, timedelta, timezone
from .config import settings
from .db import Database
from .extraction import extract, chunk_blocks
from .llm import embed, ConfigurationError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("atlas.worker")


async def heartbeat(db: Database, job: dict):
    while True:
        await asyncio.sleep(30)
        rows = await db.update("ingestion_jobs", {"lease_until": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}, id="eq."+job["id"], attempts="eq."+str(job["attempts"]), status="eq.running")
        if not rows:
            raise RuntimeError("Job lease lost")


async def process(db: Database, job: dict):
    rows = await db.select("documents", id="eq."+job["document_id"], organization_id="eq."+job["organization_id"], limit="1")
    if not rows:
        await db.update("ingestion_jobs", {"status": "done"}, id="eq."+job["id"])
        return
    document = rows[0]
    if job["kind"] == "delete":
        await db.request("DELETE", "/storage/v1/object/company-documents", json={"prefixes": [document["storage_path"]]})
        await db.delete("chunks", document_id="eq."+document["id"], organization_id="eq."+document["organization_id"])
        await db.update("ingestion_jobs", {"status": "done", "lease_until": None}, id="eq."+job["id"])
        return
    if document["status"] == "deleted":
        await db.update("ingestion_jobs", {"status": "done"}, id="eq."+job["id"])
        return
    lease_task = asyncio.create_task(heartbeat(db, job))
    try:
        async with asyncio.timeout(300):
            filters = {"id": "eq."+document["id"], "status": "neq.deleted", "organization_id": "eq."+document["organization_id"]}
            await db.update("documents", {"status": "extracting"}, **filters)
            result = await db.request("GET", "/storage/v1/object/company-documents/"+document["storage_path"])
            blocks, note = await asyncio.to_thread(extract, result.content, document["name"])
            await db.update("documents", {"status": "chunking"}, **filters)
            chunks = chunk_blocks(blocks)
            if len(chunks) > settings().max_chunks:
                raise ValueError("Document is too large to index. Split it into smaller files.")
            await db.delete("chunks", document_id="eq."+document["id"], organization_id="eq."+document["organization_id"])
            await db.update("documents", {"status": "embedding"}, **filters)
            for start in range(0, len(chunks), 32):
                if lease_task.done():
                    lease_task.result()
                current = await db.select("documents", id="eq."+document["id"], select="status", limit="1")
                if not current or current[0]["status"] == "deleted":
                    await db.delete("chunks", document_id="eq."+document["id"])
                    await db.update("ingestion_jobs", {"status": "done"}, id="eq."+job["id"])
                    return
                batch = chunks[start:start+32]
                vectors = await embed([chunk.text for chunk in batch])
                await db.insert("chunks", [{"organization_id": document["organization_id"], "document_id": document["id"], "ordinal": start+i, "content": chunk.text, "location": chunk.location, "embedding": vector, "embedding_model": settings().embedding_model} for i, (chunk, vector) in enumerate(zip(batch, vectors))], upsert=True)
            published = await db.rpc("publish_document", {"doc": document["id"], "job": job["id"], "expected_attempt": job["attempts"], "note": note})
            if not published:
                await db.delete("chunks", document_id="eq."+document["id"])
            logger.info("job=%s complete chunks=%s published=%s", job["id"], len(chunks), published)
    except Exception as error:
        terminal = isinstance(error, (ValueError, ConfigurationError)) or job["attempts"] >= 3
        message = str(error)[:240] if isinstance(error, (ValueError, ConfigurationError)) else "Processing interrupted. Please retry this document."
        await db.update("ingestion_jobs", {"status": "failed" if terminal else "queued", "lease_until": None, "last_error": message, "available_at": (datetime.now(timezone.utc)+timedelta(seconds=10*job["attempts"])).isoformat()}, id="eq."+job["id"], attempts="eq."+str(job["attempts"]))
        await db.update("documents", {"status": "failed" if terminal else "queued", "error_message": message}, id="eq."+document["id"], status="neq.deleted")
        logger.warning("job=%s failed type=%s", job["id"], type(error).__name__)
    finally:
        lease_task.cancel()
        await asyncio.gather(lease_task, return_exceptions=True)


async def main():
    db = Database(privileged=True)
    while True:
        try:
            jobs = await db.rpc("claim_job", {})
            if jobs:
                await process(db, jobs[0])
            else:
                await asyncio.sleep(settings().worker_poll_seconds)
        except Exception as error:
            logger.error("Worker connectivity error: %s", type(error).__name__)
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
