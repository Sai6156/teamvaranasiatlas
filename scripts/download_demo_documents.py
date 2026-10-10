"""Download original public company documents and build auditable local text."""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.extraction import Block, chunk_blocks
from atlas.pdf_extract import extract_pdf

os.environ["TESSDATA_PREFIX"] = str(ROOT / ".runtime/tessdata")

CATALOG = ROOT / "demo-data/source-catalog.json"
MANIFEST = ROOT / "demo-data/download-manifest.json"


def html_blocks(data: bytes):
    soup = BeautifulSoup(data, "html.parser")
    for node in soup.select("script,style,nav,header,footer,svg,noscript"):
        node.decompose()
    main = soup.find("main")
    root = main if main and len(main.get_text(" ", strip=True)) > 400 else soup
    for table in root.find_all("table"):
        rows = [[cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"], recursive=False)] for row in table.find_all("tr")]
        rows = [row for row in rows if row]
        table.replace_with(soup.new_string("\n" + "\n".join(" | ".join(row) for row in rows) + "\n"))
    text = root.get_text("\n", strip=True)
    return [Block(text, {"kind": "lines", "start": 1, "end": len(text.splitlines()), "label": "Extracted text lines 1–" + str(len(text.splitlines()))})], "Complete downloaded HTML content normalized; tables retain row order."


def extract_local(path, document):
    data = path.read_bytes()
    if path.suffix == ".pdf":
        blocks, note = extract_pdf(data, detect_tables=False)
    else:
        blocks, note = html_blocks(data)
    if sum(len(block.text.strip()) for block in blocks) < 400:
        raise ValueError("Too little readable source content")
    chunks = chunk_blocks(blocks)
    for chunk in chunks:
        chunk.location["source_url"] = document["url"]
        chunk.location["period"] = document["period"]
        if chunk.location.get("kind") == "lines":
            chunk.location["label"] = "Extracted text " + chunk.location["label"].lower()
    text_path = path.parent / (document["slug"] + ".extracted.md")
    text_path.write_text("\n\n".join("## " + block.location["label"] + "\n" + block.text for block in blocks), encoding="utf-8")
    chunk_path = path.parent / (document["slug"] + ".chunks.json")
    chunk_path.write_text(json.dumps([{"text": c.text, "location": c.location} for c in chunks], ensure_ascii=False), encoding="utf-8")
    return {"chunks": len(chunks), "text_path": str(text_path.relative_to(ROOT)), "chunk_path": str(chunk_path.relative_to(ROOT)), "extraction_note": note, "pages": max((b.location.get("page", 0) for b in blocks), default=0)}


async def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"documents": []}
    known = {(d["company_slug"], d["slug"]): d for d in previous["documents"]}
    results = []
    download_gate, parse_gate = asyncio.Semaphore(4), asyncio.Semaphore(2)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36", "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"}
    async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"), headers=headers, follow_redirects=True, timeout=30) as client:
        async def download(company, doc):
            item = {**doc, "company_slug": company["slug"], "company_name": company["name"], "region": company["region"]}
            folder = ROOT / "demo-data/companies" / company["slug"]
            folder.mkdir(parents=True, exist_ok=True)
            try:
                old = known.get((company["slug"], doc["slug"]))
                if old and old.get("status") == "verified" and (ROOT / old["path"]).exists() and old["url"] == doc["url"]:
                    item = old
                else:
                    if old and old.get("path") and old["url"] == doc["url"] and (ROOT / old["path"]).resolve().is_relative_to((ROOT / "demo-data/companies").resolve()) and (ROOT / old["path"]).exists():
                        path = ROOT / old["path"]
                        item = {**old}
                        item.pop("error", None)
                    else:
                      async with download_gate:
                        response = None
                        for attempt in range(2):
                            try:
                                async with asyncio.timeout(45):
                                    response = await client.get(doc["url"])
                                    response.raise_for_status()
                                break
                            except (httpx.HTTPError, TimeoutError):
                                if attempt: raise
                                await asyncio.sleep(1)
                        data = response.content
                        if not data or len(data) > 25 * 1024 * 1024:
                            raise ValueError("Source is empty or exceeds demo file budget")
                        is_pdf = data.startswith(b"%PDF-")
                        if not is_pdf and ".pdf" in doc["url"].lower():
                            raise ValueError("Download returned HTML instead of PDF")
                        if not is_pdf and any(x in response.text.lower()[:2000] for x in ["access denied", "just a moment", "captcha"]):
                            raise ValueError("Publisher did not return the requested document")
                        path = folder / (doc["slug"] + (".pdf" if is_pdf else ".html"))
                        path.write_bytes(data)
                        item.update(path=str(path.relative_to(ROOT)), resolved_url=str(response.url), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), downloaded_at=datetime.now(timezone.utc).isoformat(), mime_type="application/pdf" if is_pdf else "text/html")
                    async with parse_gate:
                        item.update(await asyncio.to_thread(extract_local, path, doc))
                    item["status"] = "verified"
                print(json.dumps({"company": company["slug"], "document": doc["slug"], "status": item["status"], "pages": item.get("pages"), "chunks": item.get("chunks")}), flush=True)
            except Exception as error:
                item.update(status="failed", error=f"{type(error).__name__}: {str(error)[:180]}")
                print(json.dumps({"company": company["slug"], "document": doc["slug"], "status": "failed", "error": item["error"]}), flush=True)
            results.append(item)
            MANIFEST.write_text(json.dumps({"dataset": catalog["dataset"], "documents": sorted(results, key=lambda d: (d["company_slug"], d["slug"]))}, ensure_ascii=False, indent=2), encoding="utf-8")
        await asyncio.gather(*(download(company, doc) for company in catalog["companies"] for doc in company["documents"]))
    print(json.dumps({"verified": sum(d["status"] == "verified" for d in results), "total": len(results)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
