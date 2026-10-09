"""Remove only generated Atlas QA users, their workspaces, and fixture objects."""

import asyncio
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from atlas.config import Settings


async def main():
    config = Settings(_env_file=(ROOT / "services/api/.env", ROOT / "secrets.env"))
    headers = {"apikey": config.supabase_service_role_key}
    if not config.supabase_service_role_key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + config.supabase_service_role_key
    base = config.supabase_url
    removed = 0
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            base + "/auth/v1/admin/users", headers=headers, params={"per_page": 1000}
        )
        response.raise_for_status()
        users = [
            user
            for user in response.json()["users"]
            if user.get("email", "").startswith("atlas-qa-")
            and user.get("email", "").endswith("@example.com")
            and user.get("user_metadata", {})
            .get("full_name", "")
            .startswith("Atlas QA ")
        ]
        for user in users:
            response = await client.get(
                base + "/rest/v1/organizations",
                headers=headers,
                params={"created_by": "eq." + user["id"], "select": "id,name"},
            )
            response.raise_for_status()
            for org in response.json():
                if not org["name"].startswith(
                    ("Atlas QA Company ", "Isolated QA Company ")
                ):
                    continue
                docs = await client.get(
                    base + "/rest/v1/documents",
                    headers=headers,
                    params={
                        "organization_id": "eq." + org["id"],
                        "select": "storage_path",
                    },
                )
                docs.raise_for_status()
                paths = [doc["storage_path"] for doc in docs.json()]
                if paths:
                    result = await client.request(
                        "DELETE",
                        base + "/storage/v1/object/company-documents",
                        headers=headers,
                        json={"prefixes": paths},
                    )
                    result.raise_for_status()
                result = await client.delete(
                    base + "/rest/v1/organizations",
                    headers=headers,
                    params={"id": "eq." + org["id"]},
                )
                result.raise_for_status()
        # Shared fixture workspaces must be removed before any referenced user.
        for user in users:
            result = await client.delete(
                base + "/auth/v1/admin/users/" + user["id"], headers=headers
            )
            result.raise_for_status()
            removed += 1
    print({"synthetic_qa_accounts_removed": removed, "real_accounts_untouched": True})


asyncio.run(main())
