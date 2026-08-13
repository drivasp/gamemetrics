"""Metadata de los 6 reportes del Centro de Reportes."""
from __future__ import annotations

from typing import Any

REPORTS: dict[str, dict[str, Any]] = {
    "GM-S01": {
        "code": "GM-S01",
        "type": "simple",
        "title": "Cola de solicitudes de propiedad",
        "area": "Administración de Plataforma",
        "question": "¿Qué solicitudes de propiedad de juegos siguen sin decidir?",
        "description": "Listado de claims pendientes de revisión por administración.",
        "source": "fact_partner_games · submission_status = pending",
        "columns": [
            {"key": "game_name", "label": "Juego", "align": "left"},
            {"key": "company_name", "label": "Estudio", "align": "left"},
            {"key": "contact_email", "label": "Correo", "align": "left"},
            {"key": "product_id", "label": "Product ID", "align": "left"},
            {"key": "submission_status", "label": "Estado", "align": "left"},
            {"key": "created_at_iso", "label": "Solicitado", "align": "right"},
        ],
        "filters": ["status"],
    },
    "GM-S02": {
        "code": "GM-S02",
        "type": "simple",
        "title": "Historial de liquidaciones",
        "area": "Administración de Plataforma",
        "question": "¿Qué pagos a estudios ya quedaron registrados?",
        "description": "Liquidaciones (payouts) pagadas a publishers, con método y referencia.",
        "source": "fact_partner_payouts",
        "columns": [
            {"key": "payout_id", "label": "Payout ID", "align": "left"},
            {"key": "partner_id", "label": "Partner ID", "align": "left"},
            {"key": "company_name", "label": "Estudio", "align": "left"},
            {"key": "amount", "label": "Monto (USD)", "align": "right"},
            {"key": "method", "label": "Método", "align": "left"},
            {"key": "status", "label": "Estado", "align": "left"},
            {"key": "reference", "label": "Referencia", "align": "left"},
            {"key": "paid_at_iso", "label": "Pagado", "align": "right"},
        ],
        "filters": [],
    },
    "GM-S03": {
        "code": "GM-S03",
        "type": "simple",
        "title": "Tickets de soporte abiertos",
        "area": "Atención al Cliente",
        "question": "¿Qué solicitudes de ayuda siguen abiertas?",
        "description": "Tickets con estado open, ordenados por prioridad y fecha.",
        "source": "fact_support_tickets · status = open",
        "columns": [
            {"key": "ticket_id", "label": "Ticket", "align": "left"},
            {"key": "user_id", "label": "Usuario", "align": "left"},
            {"key": "subject", "label": "Asunto", "align": "left"},
            {"key": "priority", "label": "Prioridad", "align": "left"},
            {"key": "status", "label": "Estado", "align": "left"},
            {"key": "created_at_iso", "label": "Creado", "align": "right"},
        ],
        "filters": ["status"],
    },
    "GM-C01": {
        "code": "GM-C01",
        "type": "compound",
        "title": "Resumen económico de plataforma",
        "area": "Administración de Plataforma",
        "question": "¿Cuánto GMV, comisión y adeudo a publishers acumula GameMetrics?",
        "description": "Indicadores agregados de GMV, ingresos de plataforma y saldo adeudado.",
        "source": "fact_partner_ledger (agregación OLAP)",
        "columns": [
            {"key": "metric", "label": "Indicador", "align": "left"},
            {"key": "value", "label": "Valor", "align": "right"},
            {"key": "unit", "label": "Unidad", "align": "left"},
        ],
        "filters": [],
    },
    "GM-C02": {
        "code": "GM-C02",
        "type": "compound",
        "title": "Ganancias por estudio",
        "area": "Distribución B2B",
        "question": "¿Cuánto ha ganado un estudio (bruto, fee, neto y saldo disponible)?",
        "description": "Resumen de earnings de un publisher con desglose por juego.",
        "source": "fact_partner_ledger · fact_partner_payouts",
        "columns": [
            {"key": "game_name", "label": "Juego", "align": "left"},
            {"key": "units_sold", "label": "Unidades", "align": "right"},
            {"key": "gross_revenue", "label": "Bruto (USD)", "align": "right"},
            {"key": "platform_fee", "label": "Comisión (USD)", "align": "right"},
            {"key": "publisher_net", "label": "Neto (USD)", "align": "right"},
        ],
        "filters": ["partner_id"],
    },
    "GM-C03": {
        "code": "GM-C03",
        "type": "compound",
        "title": "Desempeño comercial por estudio",
        "area": "Ventas y Marketing",
        "question": "¿Qué estudios venden más y cuáles concentran más reembolsos?",
        "description": "Rollup por partner: unidades, bruto, comisión, neto y reembolsos.",
        "source": "fact_partner_accounts + fact_partner_ledger",
        "columns": [
            {"key": "company_name", "label": "Estudio", "align": "left"},
            {"key": "games_count", "label": "Juegos", "align": "right"},
            {"key": "units_sold", "label": "Unidades", "align": "right"},
            {"key": "gross_revenue", "label": "Bruto (USD)", "align": "right"},
            {"key": "platform_fee", "label": "Comisión (USD)", "align": "right"},
            {"key": "publisher_net", "label": "Neto (USD)", "align": "right"},
            {"key": "refund_count", "label": "Reembolsos", "align": "right"},
            {"key": "status", "label": "Estado", "align": "left"},
        ],
        "filters": [],
    },
}


def list_catalog() -> list[dict[str, Any]]:
    order = ["GM-S01", "GM-S02", "GM-S03", "GM-C01", "GM-C02", "GM-C03"]
    return [REPORTS[c] for c in order]


def get_meta(code: str) -> dict[str, Any] | None:
    return REPORTS.get((code or "").upper())
