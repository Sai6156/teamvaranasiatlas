"""Real-report regression. Expected values are test oracles, never model inputs."""

import asyncio
import hashlib
import json
import re
import secrets
import sys
import time
from pathlib import Path
from uuid import uuid4
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings

ORG = "25bd4a71-daa4-4332-9cf7-ff2d08666c49"
REPORT_IDS = [
    "35dbc2fc-c7eb-424c-af66-7d09e40a5582",
    "c0c30ce7-ea7e-49e0-8e1c-2fc325894aee",
]
CASES = [
    (
        "Turnover and NIC",
        "Identify the largest turnover-contributing product/service. Give its exact description, NIC code, and percentage of turnover.",
        [
            "19201",
            "65.02",
            "production of liquid and gaseous fuels",
            "bituminous minerals",
        ],
    ),
    (
        "Related parties",
        "Give the FY2024-25 percentages of related-party purchases, sales, and investments.",
        ["40.77", "57.02", "64.87"],
    ),
    (
        "ESG investment",
        "What percentages of FY2024-25 R&D and capital expenditure investments were for environmental/social improvements?",
        ["36.64", "63.36"],
    ),
    (
        "Payable days",
        "What were the days of accounts payable in FY2024-25 and FY2023-24?",
        ["101", "100"],
    ),
    (
        "Differently abled headcount",
        "How many differently abled employees and workers were there, what was their combined total, and how many were female?",
        ["13", "24", "37", "2"],
    ),
    (
        "Safety",
        "For FY2024-25, give total recordable work-related injuries and high-consequence work-related injuries separately for employees and workers.",
        ["14", "31", "0"],
    ),
    (
        "ESG committee",
        "Name the committee responsible for sustainability and list all its members, their committee roles, and director designations.",
        [
            "ESG",
            "Hital",
            "Meswani",
            "Prasad",
            "Arundhati",
            "Bhattacharya",
            "Chairman",
            "Independent",
        ],
    ),
    (
        "Female turnover",
        "Give permanent female employee turnover rates for FY2024-25, FY2023-24, and FY2022-23, in that order. Then give female worker rates in the same order.",
        ["18", "19", "20", "25", "21", "12"],
    ),
    (
        "Recycling",
        "Give exact FY2024-25 quantities of plastics recycled and safely disposed in metric tonnes, and the percentage of POY reclaimed. Use the disclosure tables rather than rounded infographic figures.",
        ["29464", "33400", "73"],
    ),
    (
        "Locations and markets",
        "Give national and international plant counts, national and international office counts, their separate totals, and the number of export countries served.",
        ["15", "0", "62", "2", "64", "108"],
    ),
]


def normalized(text):
    return re.sub(r"[^a-z0-9.]", "", text.lower())


def check(answer, sources, index):
    clean = normalized(answer)
    without_citations = re.sub(r"\[\d+\]", "", answer)
    numbers = {
        number.replace(",", "")
        for number in re.findall(
            r"(?<![a-zA-Z0-9])\d[\d,]*(?:\.\d+)?", without_citations
        )
    }
    missing = [
        term
        for term in CASES[index][2]
        if (
            term not in numbers
            if re.fullmatch(r"\d+(?:\.\d+)?", term)
            else normalized(term) not in clean
        )
    ]
    # The BRSR prints this surname incorrectly. Accept a verbatim transcription
    # only when the answer and uploaded evidence contain that exact spelling.
    # This evaluation exception is never supplied to the application or model.
    if index == 6 and "Bhattacharya" in missing:
        source_variant = "Arundhati Bhattacharaya"
        if source_variant.lower() in answer.lower() and any(
            source_variant.lower() in source["content"].lower() for source in sources
        ):
            missing.remove("Bhattacharya")
    if index == 7:
        # Check order and association, not just that six percentages occur anywhere.
        compact = re.sub(r"[^a-z0-9%]", "", answer.lower())
        employee = bool(
            re.search(r"employ\w{0,8}.*?18(?:%|fy).*?19(?:%|fy).*?20", compact)
        )
        worker = bool(
            re.search(r"worker\w{0,8}.*?25(?:%|fy).*?21(?:%|fy).*?12", compact)
        )
        year_rows = all(
            re.search(year + r".{0,70}?" + left + r"%?.{0,30}?" + right + r"%", compact)
            for year, left, right in [
                ("202425", "18", "25"),
                ("202324", "19", "21"),
                ("202223", "20", "12"),
            ]
        )
        if not ((employee and worker) or year_rows):
            missing.append("ordered female employee/worker year associations")
    if not sources:
        missing.append("source citations")
    return missing


async def parse_chat(client, base, headers, org, question):
    started = time.monotonic()
    first_token = None
    answer = ""
    sources = []
    error = None
    async with client.stream(
        "POST",
        base + f"/workspaces/{org}/chat",
        headers=headers,
        json={"question": question},
        timeout=180,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            item = json.loads(line[5:].strip())
            if item["type"] == "token":
                if first_token is None:
                    first_token = time.monotonic() - started
                answer += item["text"]
            elif item["type"] == "reset":
                answer = item["text"]
            elif item["type"] == "done":
                sources = item["citations"]
            elif item["type"] == "error":
                error = item["text"]
    return {
        "answer": answer,
        "sources": sources,
        "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "first_token_seconds": round(first_token, 2) if first_token else None,
    }


async def main():
    config = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
    admin = {"apikey": config.supabase_service_role_key}
    if not config.supabase_service_role_key.startswith("sb_secret_"):
        admin["Authorization"] = "Bearer " + config.supabase_service_role_key
    base = "https://atlas-varanasi-api.onrender.com"
    store = config.supabase_url
    runtime = ROOT / ".runtime/reliance"
    runtime.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=90) as client:
        # Wait on the actual live ingestion state, not a local completion marker.
        deadline = time.monotonic() + 1800
        while time.monotonic() < deadline:
            response = await client.get(
                store + "/rest/v1/documents",
                headers=admin,
                params={
                    "id": "in.(" + ",".join(REPORT_IDS) + ")",
                    "organization_id": "eq." + ORG,
                },
            )
            response.raise_for_status()
            reports = response.json()
            if any(report["status"] == "failed" for report in reports):
                raise RuntimeError(
                    "A live report failed indexing: "
                    + str(
                        [
                            (r["name"], r["error_message"])
                            for r in reports
                            if r["status"] == "failed"
                        ]
                    )
                )
            if len(reports) == 2 and all(
                r["status"] == "ready" and r["indexing_version"] == "pdf-v2"
                for r in reports
            ):
                break
            print(
                json.dumps(
                    {
                        "stage": "waiting_on_live_reports",
                        "reports": [
                            {
                                k: r.get(k)
                                for k in [
                                    "name",
                                    "status",
                                    "processed_pages",
                                    "total_pages",
                                    "index_completed_chunks",
                                    "index_total_chunks",
                                ]
                            }
                            for r in reports
                        ],
                    }
                ),
                flush=True,
            )
            await asyncio.sleep(20)
        else:
            raise RuntimeError(
                "Live indexing did not finish within the verification window"
            )
        suffix = secrets.token_hex(4)
        email = f"atlas-qa-report-{suffix}@example.com"
        password = secrets.token_urlsafe(24)
        user_response = await client.post(
            store + "/auth/v1/admin/users",
            headers=admin,
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": "Atlas QA reports"},
            },
        )
        user_response.raise_for_status()
        user = user_response.json()
        login = await client.post(
            store + "/auth/v1/token?grant_type=password",
            headers={"apikey": config.supabase_publishable_key},
            json={"email": email, "password": password},
        )
        login.raise_for_status()
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        workspace = await client.post(
            base + "/workspaces",
            headers=headers,
            json={
                "name": "Atlas QA Company reports " + suffix,
                "full_name": "Atlas QA reports",
            },
        )
        workspace.raise_for_status()
        qa_org = workspace.json()["id"]
        (runtime / "qa-session.json").write_text(
            json.dumps(
                {
                    "email": email,
                    "password": password,
                    "token": login.json()["access_token"],
                    "user_id": user["id"],
                    "organization_id": qa_org,
                }
            ),
            encoding="utf-8",
        )
        report_proofs = []
        for report in reports:
            document_id = str(uuid4())
            cached = runtime / (
                "brsr.pdf" if "BRSR" in report["name"] else "annual.pdf"
            )
            data = cached.read_bytes()
            path = qa_org + "/" + document_id + "/original"
            upload = await client.post(
                store + "/storage/v1/object/company-documents/" + path,
                headers={**admin, "Content-Type": "application/pdf"},
                content=data,
            )
            upload.raise_for_status()
            metadata = {
                key: report[key]
                for key in [
                    "name",
                    "mime_type",
                    "size_bytes",
                    "collection",
                    "chunk_count",
                    "extraction_note",
                    "total_pages",
                    "processed_pages",
                    "index_total_chunks",
                    "index_completed_chunks",
                    "indexing_version",
                ]
            }
            metadata.update(
                id=document_id,
                organization_id=qa_org,
                uploaded_by=user["id"],
                status="ready",
                storage_path=path,
                content_hash=hashlib.sha256(data).hexdigest(),
            )
            added = await client.post(
                store + "/rest/v1/documents", headers=admin, json=metadata
            )
            added.raise_for_status()
            chunks = []
            offset = 0
            while True:
                result = await client.get(
                    store + "/rest/v1/chunks",
                    headers=admin,
                    params={
                        "document_id": "eq." + report["id"],
                        "select": "ordinal,content,location,embedding,embedding_model",
                        "order": "ordinal.asc",
                        "limit": "250",
                        "offset": str(offset),
                    },
                )
                result.raise_for_status()
                part = result.json()
                chunks.extend(part)
                offset += len(part)
                if len(part) < 250:
                    break
            assert len(chunks) == report["chunk_count"], (
                "No source chunk can be omitted from the regression copy"
            )
            assert (
                len({chunk["location"]["page"] for chunk in chunks})
                == report["total_pages"]
            )
            for start in range(0, len(chunks), 64):
                batch = [
                    {**chunk, "document_id": document_id, "organization_id": qa_org}
                    for chunk in chunks[start : start + 64]
                ]
                copied = await client.post(
                    store + "/rest/v1/chunks", headers=admin, json=batch
                )
                copied.raise_for_status()
            report_proofs.append(
                {
                    "name": report["name"],
                    "pages": report["total_pages"],
                    "chunks": len(chunks),
                    "all_pages_indexed": True,
                }
            )
            print(
                json.dumps({"stage": "report_copy_verified", **report_proofs[-1]}),
                flush=True,
            )
        results = []
        first_request = time.monotonic()
        for index, (name, question, _) in enumerate(CASES):
            output = await parse_chat(
                client,
                base,
                headers,
                qa_org,
                "Use the uploaded Reliance BRSR for FY2024-25. " + question,
            )
            missing = check(output["answer"], output["sources"], index)
            output.update(
                case=index + 1,
                name=name,
                passed=not missing and not output["error"],
                missing=missing,
            )
            results.append(output)
            (runtime / "evaluation.json").write_text(
                json.dumps(
                    {"reports": report_proofs, "cases": results},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        key: output[key]
                        for key in [
                            "case",
                            "name",
                            "passed",
                            "missing",
                            "error",
                            "elapsed_seconds",
                            "first_token_seconds",
                        ]
                    }
                ),
                flush=True,
            )
        if time.monotonic() - first_request < 65:
            await asyncio.sleep(65 - (time.monotonic() - first_request))
        bulk = (
            "Use the uploaded Reliance BRSR for FY2024-25. Answer every numbered question and all requested fields.\n"
            + "\n".join(f"{i + 1}. {case[1]}" for i, case in enumerate(CASES))
        )
        combined = await parse_chat(client, base, headers, qa_org, bulk)
        parts = re.split(r"(?m)^\s*###\s+(\d+)\s*$", combined["answer"])
        sections = {
            int(parts[index]): parts[index + 1] for index in range(1, len(parts) - 1, 2)
        }
        combined["field_failures"] = {
            str(index + 1): missing
            for index in range(10)
            if (missing := check(sections.get(index + 1, ""), combined["sources"], index))
        }
        combined["passed"] = (
            not combined["field_failures"]
            and not combined["error"]
            and bool(combined["sources"])
            and len(sections) == 10
        )
        summary = {
            "reports": report_proofs,
            "individual_passed": sum(result["passed"] for result in results),
            "individual_total": 10,
            "cases": results,
            "bulk": combined,
        }
        (runtime / "evaluation.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "individual_score": f"{summary['individual_passed']}/10",
                    "bulk_passed": combined["passed"],
                    "bulk_field_failures": combined["field_failures"],
                    "bulk_seconds": combined["elapsed_seconds"],
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
