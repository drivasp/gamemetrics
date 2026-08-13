# Dependencias abiertas — SOLO externas / legales / empresariales

Todo lo implementable en el repo de esta checklist ya está cerrado.
Lo que sigue **no** puede inventarse:

| ID | Tipo | Descripción |
|----|------|-------------|
| D04 | Legal | Jurisdicción, ToS, EULA, merchant of record |
| D05 | Fiscal | VAT/GST OSS; withholdings; rates reales por jurisdicción |
| D06 | Proveedor | Stripe/Adyen live keys + Connect KYC |
| D07 | Proveedor | Webhook disputes automático (requiere D06) |
| D08 | Proveedor | CDN/object storage producción + costos reales |
| D10 | Legal/AML | Community Market con dinero real / sanctions |
| D12 | Compliance | KYC/AML publishers |
| D13 | Datos | CAC/LTV live (marketing attribution) |
| D14 | Credenciales | Secrets prod (nunca en git) |

Implementado con sandbox/adapters: marketplace wallet, fraud rules, tax engine configurable, rate limit in-memory, payout sandbox_fail, audit log + Pinot schemas.
