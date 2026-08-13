# Fase 2 — Ver ganancias (Publisher + Admin)

## Publisher `/my-partner`

| Métrica | Fuente |
|---------|--------|
| GMV bruto | Ledger real (`fact_partner_ledger`) |
| Fee plataforma | Take rate acumulado |
| Neto / saldo | Suma `publisher_net_amount` |
| Por juego | Agregado por `product_id` |
| Movimientos | Ventas + reembolsos |

**Eliminado:** snapshot fake al añadir juego (`359.88` demo).

## Admin `/admin`

Dashboard vía `GET /admin/dashboard`:

| KPI | Descripción |
|-----|-------------|
| GMV total | Precio juegos pre-impuesto (neto reembolsos) |
| Ingresos GameMetrics | Comisión plataforma (take rate) |
| Adeudado publishers | Neto acumulado en ledger |
| Tabla partners | Compañía, email, **estado**, **% share**, juegos, ventas, GMV, fee, neto |

## APIs

- `GET /partners/me` → `earnings`, `ledger`, `revenue` (por producto)
- `GET /admin/dashboard` → dashboard completo (solo admin)
- `GET /admin/gmv` → compat (solo totales ledger)

## Probar

1. Publisher: registrar → añadir `product_id` de tienda → otra cuenta compra
2. `/my-partner`: ver GMV, fee, saldo y movimientos
3. Admin bootstrap → `/admin`: tabla partners con comisión y estados

```bash
cd e2e && npm run test:dinero
```
