"""Recheck the prepared, isolated real-report corpus on the deployed API."""

import asyncio, json, re, sys
import httpx
from evaluate_reliance_reports import CASES, check, parse_chat, ROOT

sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings


async def main():
    config = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
    state_file = ROOT / ".runtime/reliance/qa-session.json"
    state = json.loads(state_file.read_text())
    base = "https://atlas-varanasi-api.onrender.com"
    async with httpx.AsyncClient(timeout=180) as client:
        login = await client.post(
            config.supabase_url + "/auth/v1/token?grant_type=password",
            headers={"apikey": config.supabase_publishable_key},
            json={"email": state["email"], "password": state["password"]},
        )
        login.raise_for_status()
        state["token"] = login.json()["access_token"]
        state_file.write_text(json.dumps(state))
        headers = {"Authorization": "Bearer " + state["token"]}
        org = state["organization_id"]
        original = json.loads(
            (ROOT / ".runtime/reliance/evaluation.json").read_text(encoding="utf-8")
        )
        original["previous_attempt"] = {
            "individual_passed": original.get("individual_passed"),
            "bulk_passed": original.get("bulk", {}).get("passed"),
        }
        gate = asyncio.Semaphore(2)
        results = []

        async def run(index):
            async with gate:
                name, question, _ = CASES[index]
                response = await parse_chat(
                    client,
                    base,
                    headers,
                    org,
                    "Use the uploaded Reliance BRSR for FY2024-25. " + question,
                )
                missing = check(response["answer"], response["sources"], index)
                response.update(
                    case=index + 1,
                    name=name,
                    passed=not missing and not response["error"],
                    missing=missing,
                )
                results.append(response)
                print(
                    json.dumps(
                        {
                            key: response[key]
                            for key in [
                                "case",
                                "passed",
                                "missing",
                                "error",
                                "elapsed_seconds",
                            ]
                        }
                    ),
                    flush=True,
                )

        started = asyncio.get_running_loop().time()
        await asyncio.gather(*(run(index) for index in range(10)))
        elapsed = asyncio.get_running_loop().time() - started
        if elapsed < 65:
            await asyncio.sleep(65 - elapsed)
        prompt = (
            "Use the uploaded Reliance BRSR for FY2024-25. Answer every numbered question and all requested fields.\n"
            + "\n".join(f"{index + 1}. {case[1]}" for index, case in enumerate(CASES))
        )
        bulk = await parse_chat(client, base, headers, org, prompt)
        parts = re.split(r"(?m)^\s*###\s+(\d+)\s*$", bulk["answer"])
        sections = {
            int(parts[index]): parts[index + 1] for index in range(1, len(parts) - 1, 2)
        }
        failures = {
            str(index + 1): check(sections.get(index + 1, ""), bulk["sources"], index)
            for index in range(10)
        }
        bulk["field_failures"] = {
            key: value for key, value in failures.items() if value
        }
        bulk["passed"] = (
            not bulk["error"] and not bulk["field_failures"] and len(sections) == 10
        )
        results.sort(key=lambda result: result["case"])
        original.update(
            cases=results,
            individual_passed=sum(result["passed"] for result in results),
            bulk=bulk,
        )
        (ROOT / ".runtime/reliance/evaluation.json").write_text(
            json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "individual_score": f"{original['individual_passed']}/10",
                    "bulk_passed": bulk["passed"],
                    "bulk_errors": bulk["field_failures"],
                    "bulk_error": bulk["error"],
                    "bulk_seconds": bulk["elapsed_seconds"],
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
