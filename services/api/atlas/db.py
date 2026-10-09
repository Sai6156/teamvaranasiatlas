import httpx
from fastapi import HTTPException
from .config import settings


class Database:
    def __init__(self, token: str | None = None, privileged: bool = False):
        config = settings()
        key = config.supabase_service_role_key if privileged else config.supabase_publishable_key
        if not config.supabase_url or not key:
            raise HTTPException(503, "Secure workspace services are not configured yet.")
        self.base = config.supabase_url.rstrip("/")
        self.headers = {"apikey": key}
        if token or not key.startswith(("sb_secret_", "sb_publishable_")):
            self.headers["Authorization"] = f"Bearer {token or key}"

    async def request(self, method: str, path: str, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        async with httpx.AsyncClient(timeout=45) as client:
            result = await client.request(method, self.base + path, headers=headers, **kwargs)
        if result.is_error:
            try:
                detail = result.json().get("message") or result.json().get("msg") or "Workspace request failed"
            except ValueError:
                detail = "Workspace request failed"
            if result.status_code in (401, 403):
                raise HTTPException(result.status_code, "Your session expired or access was denied.")
            if result.status_code == 409:
                raise HTTPException(409, "This document has already been uploaded to this workspace.")
            # Database exception messages are intentionally authored in the migration.
            if result.status_code == 400 and result.headers.get("content-type", "").startswith("application/json"):
                raise HTTPException(400, str(detail)[:240])
            raise HTTPException(502, "Workspace service is temporarily unavailable.")
        return result

    async def rpc(self, name: str, payload: dict):
        result = await self.request("POST", "/rest/v1/rpc/" + name, json=payload)
        return result.json() if result.content else None

    async def select(self, table: str, **params):
        result = await self.request("GET", "/rest/v1/" + table, params=params)
        return result.json()

    async def insert(self, table: str, data, upsert: bool = False):
        prefer = "return=representation" + (",resolution=merge-duplicates" if upsert else "")
        result = await self.request("POST", "/rest/v1/" + table, json=data, headers={"Prefer": prefer})
        return result.json()

    async def update(self, table: str, data: dict, **params):
        result = await self.request("PATCH", "/rest/v1/" + table, json=data, params=params, headers={"Prefer": "return=representation"})
        return result.json()

    async def delete(self, table: str, **params):
        await self.request("DELETE", "/rest/v1/" + table, params=params)
