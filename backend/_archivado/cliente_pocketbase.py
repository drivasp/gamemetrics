import base64
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")


def decode_token_id(token: str) -> str:
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        return payload.get("id", "")
    except Exception:
        return ""


def avatar_url(record_id: str, filename: str) -> str | None:
    if not filename:
        return None
    return f"/pb/api/files/users/{record_id}/{filename}"


def map_user(record: dict) -> dict:
    return {
        "id": record.get("id", ""),
        "email": record.get("email", ""),
        "display_name": record.get("displayName") or record.get("display_name") or "",
        "bio": record.get("bio") or "",
        "avatar": avatar_url(record.get("id", ""), record.get("avatar", "") or ""),
    }


async def pb_post(path: str, data: dict, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.post(f"{PB_URL}{path}", json=data, headers=headers)
        r.raise_for_status()
        return r.json()


async def pb_get(
    path: str, token: str | None = None, params: dict[str, Any] | None = None
) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(f"{PB_URL}{path}", headers=headers, params=params)
        r.raise_for_status()
        return r.json()


async def pb_patch(path: str, data: dict, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.patch(f"{PB_URL}{path}", json=data, headers=headers)
        r.raise_for_status()
        return r.json()


async def pb_patch_form(
    path: str, files: dict, token: str | None = None
) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.patch(f"{PB_URL}{path}", files=files, headers=headers)
        r.raise_for_status()
        return r.json()


async def pb_delete(path: str, token: str | None = None) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.delete(f"{PB_URL}{path}", headers=headers)
        r.raise_for_status()
