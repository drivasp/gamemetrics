# Fase 3 — Regiones, precios e impuestos

Sistema comercial multi-país: el catálogo usa regiones de precio (**US / EU / LATAM**) y el checkout aplica impuestos reales por **país de facturación**.

## Países soportados

| País | Región precio | Moneda | Impuesto |
|------|---------------|--------|----------|
| US | US | USD | 0% (digital exempt demo) |
| CA | US | USD | GST 5% |
| MX | LATAM | USD | IVA 16% |
| CO | LATAM | USD | IVA 19% |
| AR | LATAM | USD | IVA 21% |
| CL | LATAM | USD | IVA 19% |
| PE | LATAM | USD | IGV 18% |
| BR | LATAM | USD | 0% (demo) |
| ES | EU | EUR | IVA 21% |
| FR | EU | EUR | TVA 20% |
| DE | EU | EUR | MwSt 19% |
| IT | EU | EUR | IVA 22% |
| GB | EU | EUR | VAT 20% |

Multiplicadores de catálogo (`fact_price_catalog`): US ×1.0 · EU ×0.92 · LATAM ×0.85.

## APIs

- `GET /locale/countries` — listado (para el formulario de registro)
- `GET /locale/me` — país de la cuenta (bloqueado)
- `PUT /locale/me` → **403** (anti-evasión)
- `POST /auth/register` requiere `country_code`
- `GET /cart` / `POST /checkout` — siempre el país de la cuenta logueada

## País de residencia (anti-evasión)

Como en Steam, el **país se elige al registrarse** y queda bloqueado:

- `POST /auth/register` requiere `country_code`
- `PUT /locale/me` → **403** (no se puede cambiar desde la tienda)
- Navbar muestra el país con candado (solo lectura)
- Carrito/checkout usan siempre el país de la cuenta

Incluye Ecuador (EC, IVA 15%, LATAM).


## Setup tablas Pinot

```bash
curl -X POST http://localhost:5000/etl/create-locale-tax-tables
# o desde el contenedor: python 18_create_locale_tax_tables.py
```

Tablas: `fact_user_locale`, `fact_order_taxes`.

## Prueba E2E

```bash
cd e2e
npm run test:fase3
```
