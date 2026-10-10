from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from atlas.main import member, workspaces

ORG = UUID("11111111-1111-1111-1111-111111111111")


class DemoDB:
    def __init__(self, published=True):
        self.published = published
        self.calls = []

    async def select(self, table, **params):
        self.calls.append((table, params))
        if table == "memberships":
            return []
        return [{"id": str(ORG), "name": "Public Example", "is_demo": True}] if self.published else []


@pytest.mark.asyncio
async def test_verified_demo_access_is_read_only():
    db = DemoDB()
    auth = SimpleNamespace(db=db, user={"id": "judge"})
    assert (await member(auth, ORG))["role"] == "employee"
    assert db.calls[-1][1]["demo_ready"] == "eq.true"
    with pytest.raises(HTTPException) as error:
        await member(auth, ORG, admin=True)
    assert error.value.status_code == 403
    assert db.calls[-1][0] == "memberships"


@pytest.mark.asyncio
async def test_unpublished_demo_and_unrelated_company_are_denied():
    auth = SimpleNamespace(db=DemoDB(published=False), user={"id": "judge"})
    with pytest.raises(HTTPException) as error:
        await member(auth, ORG)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_catalog_never_grants_admin_role():
    auth = SimpleNamespace(db=DemoDB(), user={"id": "judge"})
    rows = await workspaces(auth)
    assert len(rows) == 1 and rows[0]["role"] == "employee"
