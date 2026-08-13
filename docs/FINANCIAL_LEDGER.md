# Ledger financiero durable (plataforma)

## Separación de responsabilidades

| Capa | Tecnología | Rol |
|------|------------|-----|
| **Source of truth** | SQLite (`financial_transactions`) vía `ledger/sqlite_store.py` | Movimientos de dinero con UNIQUE(idempotency_key); balance = SUM(amount) |
| **Event bus** | Kafka | Replica eventos a consumidores (wallet analytics, market_*, partner ledger Pinot) |
| **Analytics** | Apache Pinot | Lecturas operativas / reportes (consistencia eventual) |

## Qué NO es

No es un ledger bancario regulado. No almacena PAN/CVV. El PSP (Stripe) sigue siendo merchant processor cuando exista.

## Idempotencia

Toda operación financiera crítica usa `idempotency_key` única en SQLite:
- wallet topup / purchase / refund
- marketplace buyer/seller/fees
- partner sale / refund / payout

Un replay (webhook, doble click, re-fulfill) **no duplica dinero**.

## Path

`FINANCIAL_LEDGER_PATH` (default `backend/data/financial_ledger.sqlite3`; Docker `/app/data/...`).

## Endpoint público `/marketplace/fees`

**Permanece público** porque es solo preview/calculadora:

- no modifica balances
- no crea transacciones ni listings
- no ejecuta pagos ni cambia ownership
- no escribe en el ledger

Respuesta incluye `mutates_money: false`. Cubierto por `test_durable_ledger.py` y E2E `audit-cierre.spec.ts`.
