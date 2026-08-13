# Dinero en cada venta — Ledger B2B

## Modelo (estilo Steam / Epic)

| Concepto | Regla |
|----------|--------|
| **Gross** | Precio del juego × cantidad (**pre-impuesto**) |
| **Publisher share** | `%` en `fact_partner_accounts.revenue_share_pct` (default **70%**) |
| **Platform fee (take rate)** | `100% − publisher share` (default **30%**) |
| **Impuestos** | En `fact_order_taxes`; **no** se reparten con el publisher |
| **Sin partner** | Juego del catálogo sin `fact_partner_games` → sin asiento (first-party) |

## Persistencia

Tabla Pinot REALTIME `fact_partner_ledger` (Kafka topic homónimo).

- PK determinista venta: `sale_{order_id}_{product_id}` (idempotente ante re-fulfill)
- PK reembolso: `refund_{purchase_id}`
- Campos: gross, platform_fee, publisher_net, % auditables, status `available`

## Flujo

1. Checkout `fulfill_order` → por ítem `record_sale_ledger`
2. `POST /refunds` → `record_refund_ledger` (asiento inverso)
3. Publisher: `GET /partners/me` → `earnings` + `ledger` reales
4. Admin: `GET /admin/gmv` → GMV, ingreso plataforma, adeudado a publishers

## Setup tabla

```bash
docker compose exec etl-api python 20_create_partner_ledger_table.py
```

## Qué quedó fuera (siguiente)

Payouts bancarios, hold period (ej. 14 días pending→available), facturas fiscales publisher.
