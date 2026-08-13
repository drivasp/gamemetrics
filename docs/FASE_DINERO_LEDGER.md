# Dinero en cada venta — Ledger B2B

## Modelo (estilo Steam / Epic)

| Concepto | Regla |
|----------|--------|
| **Gross** | Precio del juego × cantidad (**pre-impuesto**) |
| **Publisher share** | `%` en `fact_partner_accounts.revenue_share_pct` (default **70%**) en modo `flat` |
| **Platform fee (take rate)** | `100% − publisher share` (default **30%**) |
| **Modo `steam_tiers`** | 30% / 25% / 20% por lifetime AGR del producto (ver `revenue_share.py`) |
| **Impuestos** | En `fact_order_taxes`; **no** se reparten con el publisher |
| **Sin partner** | Juego del catálogo sin `fact_partner_games` → sin asiento (first-party) |
| **Direct fee** | `PUBLICATION_FEE_USD` al aprobar claim; recoup a `PUBLICATION_FEE_RECOUP_USD` AGR |
| **Chargeback** | Asiento `chargeback` (admin API); webhook PSP pendiente |

## Persistencia

Tabla Pinot REALTIME `fact_partner_ledger` (Kafka topic homónimo).

- PK determinista venta: `sale_{order_id}_{product_id}` (idempotente ante re-fulfill)
- PK reembolso: `refund_{purchase_id}`
- PK chargeback: `cb_{payment_id}_{product_id}`
- PK direct fee / recoup: `dfee_*` / `dfeer_*`
- Campos: gross, platform_fee, publisher_net, % auditables, status `available`
- Tipos: `sale` | `refund` | `chargeback` | `direct_fee` | `direct_fee_recoup` | `payout`

## Flujo

1. Checkout `fulfill_order` → por ítem `record_sale_ledger` (+ intento de recoup Direct fee)
2. `POST /refunds` → `record_refund_ledger` (asiento inverso; anti-duplicado)
3. `POST /admin/chargebacks` → asiento chargeback
4. Aprobar claim → `charge_publication_fee`
5. Publisher: `GET /partners/me` → `earnings` + `financial_statement` + `ledger`
6. Admin: `GET /admin/gmv`, `/admin/finance/policy`, `/admin/partners/{id}/statement`

## Setup tabla

```bash
docker compose exec etl-api python 20_create_partner_ledger_table.py
```

## Docs relacionados

- `docs/BUSINESS_MODEL_PLATFORM.md`
- `docs/OPEN_DEPENDENCIES.md`
- `docs/INFORME_FINAL_PLATAFORMA.md`
