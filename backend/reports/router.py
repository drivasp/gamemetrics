"""API Centro de Reportes — informes tácticos simples y compuestos."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import Response

from reports.catalog import get_meta
from reports.service import build_report, catalog_payload, to_csv
from shared.auth_deps import require_roles

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/catalog")
async def list_reports(authorization: Annotated[str | None, Header()] = None):
    """Catálogo de informes (evita choque con la ruta SPA /reports)."""
    await require_roles(authorization, "admin")
    return catalog_payload()


@router.get("/view/{code}")
async def get_report(
    code: str,
    status: str | None = Query(None),
    partner_id: str | None = Query(None),
    week: int | None = Query(None, ge=1, le=17),
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    if not get_meta(code):
        raise HTTPException(404, f"Informe no encontrado: {code}")
    try:
        return await build_report(code, status=status, partner_id=partner_id, week=week)
    except KeyError:
        raise HTTPException(404, f"Informe no encontrado: {code}")
    except Exception as e:
        raise HTTPException(502, f"No se pudo generar el informe: {e}")


@router.get("/view/{code}/export.csv")
async def export_report_csv(
    code: str,
    status: str | None = Query(None),
    partner_id: str | None = Query(None),
    week: int | None = Query(None, ge=1, le=17),
    authorization: Annotated[str | None, Header()] = None,
):
    await require_roles(authorization, "admin")
    if not get_meta(code):
        raise HTTPException(404, f"Informe no encontrado: {code}")
    try:
        payload = await build_report(code, status=status, partner_id=partner_id, week=week)
    except Exception as e:
        raise HTTPException(502, f"No se pudo generar el CSV: {e}")
    body = to_csv(payload)
    filename = f"{code.upper()}_{int(time.time())}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
