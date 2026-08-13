# Fase 3 — Payouts + Fase 4 — SaaS

## Investigación (Steam / industria)

| Steamworks | GameMetrics |
|------------|-------------|
| Paga ~30 días después del mes | Hold configurable (`PAYOUT_HOLD_MS`, default 0 en local; 14d en prod) |
| Mínimo ~$100 | `PAYOUT_MIN_USD` (default $1 local / $100 recomendado prod) |
| EFT + referencia | Admin marca **pagado** + referencia; opcional **Stripe Connect Transfer** |
| Portal partner ve sales/payment | `/my-partner`: available / pending / paid |

SaaS white-label (Xsolla / Bruii style): plan mensual + branding + featured de pago.

## Fase 3 — APIs

- `POST /admin/payouts` `{ partner_id, amount, method: manual|stripe_connect, reference }`
- `GET /admin/payouts`
- `GET /admin/partners/{id}/balance`
- `POST /partners/connect/onboard` (Stripe Express)
- `GET /partners/connect/status`

Tablas: `fact_partner_payouts`, `fact_partner_payout_accounts`

## Fase 4 — APIs

- `POST /partners/saas/subscribe` `{ plan_id: free|pro|studio }`
- `PUT /partners/branding` (requiere Pro/Studio)
- `GET /partners/branding/{partner_id}` público
- `POST /partners/featured/buy` → destacado en `/store/featured`

Tablas: `fact_saas_subscriptions`, `fact_partner_branding`, `fact_featured_placements`

Planes: Free $0 · Pro $29 · Studio $79

## Setup

```bash
docker compose exec etl-api python 21_create_payout_saas_tables.py
# o copiar script al contenedor si la imagen no lo trae
docker compose up -d --build backend
```

## Probar

```bash
cd e2e && npm run test:dinero && npm run test:payout-saas
```
