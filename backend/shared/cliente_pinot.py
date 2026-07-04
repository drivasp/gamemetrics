import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

PINOT_BROKER_URL = os.getenv("PINOT_BROKER_URL", "http://localhost:8099")
PINOT_QUERY_URL = f"{PINOT_BROKER_URL}/query/sql"
TIMEOUT = 8.0

TABLE = "fact_videogames"
GAME_COLUMNS = (
    "id, slug, name, released, rating, metacritic, "
    "genres, platforms, developers, publishers, esrb_rating"
)

_client: httpx.AsyncClient | None = None


class PinotUnavailableError(RuntimeError):
    """Pinot no pudo servir la consulta (segmentos caídos, broker, etc.)."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=TIMEOUT)
    return _client


async def pinot_query(sql: str, *, raise_on_error: bool = False) -> list[list[Any]]:
    print(f"[Pinot] SQL: {sql[:200]}")
    client = _get_client()
    try:
        resp = await client.post(PINOT_QUERY_URL, json={"sql": sql})
        resp.raise_for_status()
        body = resp.json()
        if body.get("exceptions"):
            print(f"[Pinot] ERROR: {body['exceptions']}")
            if raise_on_error:
                msg = body["exceptions"][0].get("message", "Pinot no disponible")
                raise PinotUnavailableError(msg)
            return []
        return (body.get("resultTable") or {}).get("rows") or []
    except PinotUnavailableError:
        raise
    except Exception as exc:
        print(f"[Pinot] ERROR: {exc}")
        if raise_on_error:
            raise PinotUnavailableError(str(exc)) from exc
        return []
