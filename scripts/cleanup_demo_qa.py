"""Remove only the two explicitly recorded temporary demo acceptance accounts."""
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings


async def main():
    config = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
    state = json.loads((ROOT / ".runtime/demo-qa.json").read_text())
    headers = {"apikey": config.supabase_service_role_key}
    async with httpx.AsyncClient(timeout=40, transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")) as client:
        for user in state["users"]:
            uid = str(UUID(user["id"]))
            assert user["email"].startswith("atlas-qa-demo-") and user["email"].endswith("@example.com")
            checked = await client.get(config.supabase_url + "/auth/v1/admin/users/" + uid, headers=headers)
            checked.raise_for_status()
            assert checked.json()["email"] == user["email"] and checked.json()["user_metadata"]["full_name"].startswith("Atlas QA Demo ")
            owned = await client.get(config.supabase_url + "/rest/v1/organizations", headers=headers, params={"created_by": "eq." + uid})
            owned.raise_for_status()
            assert not owned.json(), "Remove only this account's QA organization first"
            for table in ("conversations", "usage_events", "audit_events"):
                removed = await client.delete(config.supabase_url + "/rest/v1/" + table, headers=headers, params={"user_id": "eq." + uid})
                removed.raise_for_status()
            removed = await client.delete(config.supabase_url + "/auth/v1/admin/users/" + uid, headers=headers)
            removed.raise_for_status()
    print(json.dumps({"synthetic_accounts_removed": len(state["users"]), "company_library_untouched": True, "real_accounts_untouched": True}))


if __name__ == "__main__":
    asyncio.run(main())
