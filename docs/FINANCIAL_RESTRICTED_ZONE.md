# Financial restricted zone
#
# Source of truth for money: SQLite ledger (`ledger/sqlite_store.py`).
# Kafka = event bus. Pinot = analytics only — NEVER monetary SoT.
#
# Restricted modules (change only with financial tests green):
#   ledger/
#   wallet/servicio.py
#   checkout/partner_ledger.py
#   refunds/
#   checkout fulfill (servicio.fulfill_order)
#   marketplace buy (+ durable_store ownership)
#
# See docs/FINANCIAL_LEDGER.md and AUDITORIA_GAMEMETRICS.md §5.C
