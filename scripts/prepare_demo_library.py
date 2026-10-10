"""Prepare locally supplied reports without dropping pages or inventing facts."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.extraction import Block, chunk_blocks
from atlas.pdf_extract import clean, layout, panels, printed_pages
from download_demo_documents import html_blocks

tessdata = ROOT / ".runtime/tessdata"
if tessdata.is_dir() and "TESSDATA_PREFIX" not in os.environ:
    os.environ["TESSDATA_PREFIX"] = str(tessdata)
MANIFEST = ROOT / "demo-data/prepared-manifest.json"
DOWNLOADS = json.loads((ROOT / "demo-data/download-manifest.json").read_text())
COMPANIES = [("reliance", "Reliance Industries", "India"), ("tcs", "TCS", "India"), ("infosys", "Infosys", "India"), ("wipro", "Wipro", "India"), ("hcltech", "HCLTech", "India"), ("microsoft", "Microsoft", "Global"), ("apple", "Apple", "Global"), ("nvidia", "NVIDIA", "Global"), ("amazon", "Amazon", "Global"), ("alphabet", "Alphabet", "Global")]


def supplied(relative):
    return ROOT / "demo" / relative


def downloaded(company, slug):
    return next(d for d in DOWNLOADS["documents"] if d["company_slug"] == company and d["slug"] == slug and d["status"] == "verified")


def main():
    docs = []

    def add(company, slug, title, period, sources, collection="Reports", url=None):
        name, region = next((name, region) for key, name, region in COMPANIES if key == company)
        folder = ROOT / "demo/prepared" / company
        folder.mkdir(parents=True, exist_ok=True)
        pages = []
        original_page_count = 0
        out = folder / (slug + sources[0][0].suffix)
        if out.suffix == ".pdf":
            merged = pymupdf.open()
            for source, start, end in sources:
                with pymupdf.open(source) as pdf:
                    original_page_count += len(pdf)
                    end = len(pdf) if end is None else end
                    if not out.exists():
                        merged.insert_pdf(pdf, from_page=start, to_page=end - 1, widgets=False)
                    pages.extend({"original_document": source.name, "original_page": p + 1} for p in range(start, end))
            if not out.exists():
                merged.save(out, garbage=3, deflate=True)
            merged.close()
        else:
            shutil.copyfile(sources[0][0], out)
        data = out.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        item = dict(company_slug=company, company_name=name, region=region, slug=slug, title=title, period=period, collection=collection, path=str(out.relative_to(ROOT)), bytes=len(data), sha256=digest, mime_type="application/pdf" if pages else "text/html", source_url=url, pages=len(pages), page_map=pages, sources=[str(s[0].relative_to(ROOT)) for s in sources])
        chunkfile = folder / (slug + ".chunks.json")
        cache = folder / (slug + ".meta.json")
        if cache.exists() and json.loads(cache.read_text()).get("sha256") == digest and chunkfile.exists():
            chunks = json.loads(chunkfile.read_text(encoding="utf-8"))
            coverage = json.loads(cache.read_text())["coverage"]
        else:
            blocks, coverage = [], []
            if pages:
                with pymupdf.open(out) as pdf:
                    for i, page in enumerate(pdf):
                        origin = pages[i]
                        base = {"kind": "page", "page": i + 1, **origin, "period": period, "pipeline": "local-demo-v1", "source_url": url}
                        label = f"{origin['original_document']} · original PDF page {origin['original_page']}"
                        if len(sources) > 1 or pages[0]["original_page"] != 1 or len(pages) < original_page_count:
                            label += f" · prepared PDF page {i + 1}"
                        printed = printed_pages(page)
                        if printed:
                            label += " · printed " + "–".join(printed)
                        raw = clean(page.get_text("text"))
                        ocr = False
                        if len(raw) < 30 and page.get_images():
                            raw = clean(page.get_text(textpage=page.get_textpage_ocr(language="eng", dpi=150, full=True, tessdata=os.environ["TESSDATA_PREFIX"])))
                            ocr = True
                        if ocr:
                            blocks.append(Block(raw, {**base, "label": label + " · OCR", "ocr": True}))
                        else:
                            for n, rect in enumerate(panels(page)):
                                text = layout(page, rect)
                                if text:
                                    # One layout copy per panel; retain complete financial rows.
                                    prefix = title + " — " + period + "\n"
                                    blocks.append(Block(prefix + text, {**base, "kind": "table", "structured": False, "panel": n + 1, "label": label, "table_header": prefix}))
                        coverage.append({"page": i + 1, **origin, "characters": len(raw), "ocr": ocr, "blank": not bool(raw)})
                        pymupdf.TOOLS.store_shrink(100)
                        if (i + 1) % 100 == 0:
                            print(json.dumps({"extracting": company, "file": slug, "page": i + 1, "total": len(pdf)}), flush=True)
            else:
                blocks, _ = html_blocks(data)
                for block in blocks:
                    block.location.update(source_url=url, period=period, original_document=sources[0][0].name, pipeline="local-demo-v1")
            chunks = [{"text": b.text, "location": b.location} for b in chunk_blocks(blocks, max_chars=6000)]
            chunkfile.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
            cache.write_text(json.dumps({"sha256": digest, "coverage": coverage}, ensure_ascii=False), encoding="utf-8")
            (folder / (slug + ".extracted.md")).write_text("\n\n".join("## " + b.location["label"] + "\n" + b.text for b in blocks), encoding="utf-8")
        if not chunks or len(data) > 25 * 1024 * 1024:
            raise ValueError(f"Invalid prepared document {out}")
        item.update(chunks=len(chunks), chunk_path=str(chunkfile.relative_to(ROOT)), coverage_path=str(cache.relative_to(ROOT)), extraction_note=f"Prepared and indexed on the local PC; all {len(pages)} PDF pages examined. Original page references retained. Public historical document: {period}." if pages else f"Complete public HTML source normalized locally, tables retain row order. {period}.")
        docs.append(item)
        MANIFEST.write_text(json.dumps({"dataset": "Atlas Public Company Demo Library", "version": "local-demo-v1", "companies": [{"slug": slug, "name": name, "region": region} for slug, name, region in COMPANIES], "documents": docs}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"prepared": company, "document": slug, "pages": len(pages), "chunks": len(chunks), "bytes": len(data)}), flush=True)

    supplied_reports = {
        "reliance": ("reliance/RIL-IAR-2025.pdf", "Integrated Annual Report 2024–25", "FY 2024–25"),
        "wipro": ("wipro/Integrated-annual-report-2025-26.pdf", "Integrated Annual Report 2025–26", "FY 2025–26"),
        "hcltech": ("hcl tech/annual-report-2025-26.pdf", "Integrated Annual Report 2025–26", "FY 2025–26"),
        "microsoft": ("microsoft/Microsoft 2025 Annual Report.pdf", "Annual Report 2025", "FY 2025"),
        "nvidia": ("nvidia/2026-Annual-Report-Web.pdf", "Annual Report and Proxy 2026", "FY 2026"),
        "amazon": ("amazon/Amazon-2025-Annual-Report.pdf", "Annual Report 2025", "Calendar 2025"),
    }
    extra = {"reliance": ["fy2025-q4-results", "code-of-conduct"], "wipro": ["fy2025-q4-results", "code-of-conduct"], "hcltech": ["fy2025-q4-results", "code-of-conduct"], "microsoft": ["fy2025-q4-results", "trust-code"], "nvidia": ["fy2025-q4-results", "finance-team-code"], "amazon": ["2025-q4-results", "code-of-conduct"]}
    for company, (path, title, period) in supplied_reports.items():
        add(company, "annual-report", title, period, [(supplied(path), 0, None)])
        for slug in extra[company]:
            d = downloaded(company, slug)
            add(company, slug, d["title"], d["period"], [(ROOT / d["path"], 0, None)], "Governance" if "code" in slug else "Financials", d["url"])
    for company, path, period in [("tcs", "tcs/TCS_Annual_Report_2025-26.pdf", "FY 2025–26"), ("infosys", "infosys/infosys-ar-25.pdf", "FY 2024–25")]:
        source = supplied(path)
        with pymupdf.open(source) as pdf:
            total = len(pdf)
        for part in range(3):
            start, end = total * part // 3, total * (part + 1) // 3
            add(company, f"annual-report-part-{part + 1}", f"Annual Report {period} — Part {part + 1} of 3 (pages {start + 1}–{end})", period, [(source, start, end)])
    add("apple", "fy2026-financial-statements", "FY 2026 Q1, Q2 and Q3 Financial Statements", "FY 2026 Q1–Q3 (separate quarters)", [(supplied(f"apple/FY26_Q{q}_Consolidated_Financial_Statements.pdf"), 0, None) for q in (1, 2, 3)], "Financials")
    for company, path, title, period in [("apple", "apple/Apple_Environmental_Progress_Report_2025.pdf", "Environmental Progress Report 2025", "Published 2025, reporting FY 2024"), ("alphabet", "alphabet/download-1699a2e1.pdf", "Google Environmental Report 2026", "Published 2026")]:
        source = supplied(path)
        with pymupdf.open(source) as pdf:
            total = len(pdf)
        for part in range(2):
            start, end = total * part // 2, total * (part + 1) // 2
            add(company, f"environmental-report-part-{part + 1}", f"{title} — Part {part + 1} of 2 (pages {start + 1}–{end})", period, [(source, start, end)], "Sustainability")
    add("alphabet", "2026-q1-results", "Alphabet First Quarter 2026 Results", "Calendar 2026 Q1", [(supplied("alphabet/2026q1-alphabet-earnings-release.pdf"), 0, None)], "Financials")
    assert len(docs) == 30 and all(sum(d["company_slug"] == c for d in docs) == 3 for c, _, _ in COMPANIES)
    print(json.dumps({"complete": True, "documents": len(docs), "pages": sum(d["pages"] for d in docs), "chunks": sum(d["chunks"] for d in docs)}), flush=True)


if __name__ == "__main__":
    main()

