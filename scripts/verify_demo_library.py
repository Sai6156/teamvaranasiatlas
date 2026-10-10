"""Live acceptance checks using isolated temporary judge accounts."""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings

CONFIG = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
API = "https://atlas-varanasi-api.onrender.com"
STATE = ROOT / ".runtime/demo-qa.json"


async def main():
    state = json.loads(STATE.read_text())
    judge, outsider = state["users"]
    auth = {"Authorization": "Bearer " + judge["session"]["access_token"]}
    other = {"Authorization": "Bearer " + outsider["session"]["access_token"]}
    public = {"apikey": CONFIG.supabase_publishable_key, **auth}
    admin = {"apikey": CONFIG.supabase_service_role_key}
    started = time.monotonic()
    results = []
    async with httpx.AsyncClient(timeout=90, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
        r = await client.get(API + "/workspaces", headers=auth)
        r.raise_for_status()
        demos = [w for w in r.json() if w.get("is_demo")]
        assert len(demos) == 10 and all(w["role"] == "employee" for w in demos)
        assert sum(w["demo_region"] == "India" for w in demos) == 5
        gate = asyncio.Semaphore(3)

        async def company(w):
            async with gate:
                r = await client.get(API + f"/workspaces/{w['id']}/documents", headers=auth)
                r.raise_for_status()
                docs = r.json()
                assert len(docs) == 3 and all(d["status"] == "ready" and d["chunk_count"] > 0 for d in docs)
                for d in docs:
                    r = await client.get(API + f"/documents/{d['id']}/source", headers=auth)
                    r.raise_for_status()
                    source = await client.head(r.json()["url"])
                    source.raise_for_status()
                    assert int(source.headers.get("content-length", "0")) > 0
                row = {"company": w["name"], "documents": 3, "source_links": "verified"}
                results.append(row)
                print(json.dumps(row), flush=True)
        await asyncio.gather(*(company(w) for w in demos))
        target = demos[0]["id"]
        docs = (await client.get(API + f"/workspaces/{target}/documents", headers=auth)).json()
        assert (await client.post(API + f"/workspaces/{target}/documents", headers=auth, files={"file": ("unauthorized.txt", b"Do not insert") })).status_code == 403
        assert (await client.post(API + f"/workspaces/{target}/invitations", headers=auth, json={"email": "not-sent@example.com"})).status_code == 403
        assert (await client.delete(API + f"/documents/{docs[0]['id']}", headers=auth)).status_code in (400, 403)
        assert (await client.post(CONFIG.supabase_url + "/rest/v1/rpc/publish_demo_library", headers=public, json={"org": target})).status_code == 403
        denied = await client.patch(CONFIG.supabase_url + "/rest/v1/organizations", headers={**public, "Prefer": "return=representation"}, params={"id": "eq." + target}, json={"demo_ready": False})
        assert denied.is_error or denied.json() == []
        assert (await client.get(API + "/workspaces")).status_code == 401
        conv = await client.post(CONFIG.supabase_url + "/rest/v1/conversations", headers={**public, "Prefer": "return=representation"}, json={"organization_id": target, "user_id": judge["id"], "title": "Private judge acceptance check"})
        conv.raise_for_status()
        cid = conv.json()[0]["id"]
        hidden = await client.get(API + f"/conversations/{cid}/messages", headers=other)
        assert hidden.status_code == 404
        assert (await client.get(CONFIG.supabase_url + "/rest/v1/memberships", headers=public, params={"organization_id": "eq." + target})).json() == []
        # A private workspace is never exposed just because the catalog is shared.
        created = await client.post(API + "/workspaces", headers=auth, json={"name": "Atlas QA Company demo isolation", "full_name": "Atlas QA Demo judge"})
        created.raise_for_status()
        state["private_org"] = created.json()["id"]
        STATE.write_text(json.dumps(state))
        assert (await client.get(API + f"/workspaces/{state['private_org']}/documents", headers=other)).status_code == 403
        assert not any(w["id"] == state["private_org"] for w in (await client.get(API + "/workspaces", headers=other)).json())
        await client.delete(CONFIG.supabase_url + "/rest/v1/organizations", headers=admin, params={"id": "eq." + state["private_org"]})
        state.pop("private_org")
        STATE.write_text(json.dumps(state))
    report = {"companies": 10, "ready_sources": 30, "all_original_links_work": True, "demo_mutations_denied": True, "personal_chats_isolated": True, "private_company_isolated": True, "anonymous_access_denied": True, "seconds": round(time.monotonic() - started, 1), "company_checks": results}
    (ROOT / "demo-data/acceptance-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
