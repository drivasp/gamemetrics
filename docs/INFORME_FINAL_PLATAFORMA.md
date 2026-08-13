# Informe final — GameMetrics como plataforma de distribución

Fecha: 2026-08-12. Alcance: análisis del repo + investigación Steam + diseño BM + implementación segura verificable + pruebas unitarias financieras.

---

## 1. Qué se encontró en el proyecto

Repositorio **gamemetrics**: Angular (tienda/dashboard) + FastAPI + Kafka + Apache Pinot + ETL Docker. Ya existía un núcleo tipo Steam: auth/roles, tienda, carrito, checkout, biblioteca, wallet, refunds 14d, partners/claims, ledger 70/30, payouts, impuestos regionales demo, SaaS featured, launcher/builds, gifts, reports (20), e2e parciales.

## 2. Cómo funciona actualmente

Flujo dinero: compra → tax por país → pago (sandbox/Stripe/wallet) → fulfill → `fact_partner_ledger` (sale) → refund inverso / chargeback → balance con hold → payout admin/Connect.

## 3–6. Steam investigado / fuentes / oficiales vs estimaciones

Ver `docs/BUSINESS_MODEL_PLATFORM.md` §§2–6.

**Oficiales verificados en esta sesión:** Direct Fee $100 + recoup $1.000 AGR; pagos mensuales umbral $100 ~30 días; pricing 37 monedas; refunds 14d/&lt;2h.

**Terceros/industria:** tiers 30/25/20. **No inventados.** Epic 100% primer $1M/año luego 12% — fuente Epic Distribution.

**Valve no publica oficialmente:** margen neto corporativo; fee exacto Community Market en un único doc Steamworks claro (sesión).

## 7–17. Modelo recomendado / ingresos / costos / comisión / pagos / refunds / CB / tax / market / wallet / payouts

Ver BM doc. Resumen:
- Comisión: **30% flat** recomendada al inicio; tiers opcionales.
- Publication fee: **$100 / recoup $1k** (configurable).
- Refunds: 14d wallet credit; playtime limit **pendiente** (D09).
- Chargebacks: API admin + ledger; webhook PSP **pendiente** (D07).
- Tax: motor demo; compliance **pendiente** (D05).
- Marketplace P2P: **no** MVP (D10).
- Wallet: existe con transacciones + idempotency keys.
- Payouts: hold + min + statement.

## 18–19. Arquitectura y entidades

Mapeo en BM §8. Entidades Pinot existentes: users, purchases, payments, refunds, wallets/tx, partner_accounts/games/ledger/payouts, taxes, coupons, etc. Nuevos *tipos* de asiento ledger: `direct_fee`, `direct_fee_recoup`, `chargeback` (misma tabla).

## 20–22. Cambios realizados / archivos / migraciones

### Código nuevo
- `backend/checkout/revenue_share.py`
- `backend/checkout/direct_fee.py`
- `backend/checkout/chargebacks.py`
- `backend/checkout/financial_statement.py`
- `backend/checkout/financial_audit.py`
- `backend/tests/test_financial_integrity.py`

### Código modificado
- `backend/checkout/partner_ledger.py` — split engine, idempotencia, recoup post-sale
- `backend/checkout/partner_payouts.py` — buckets CB/fees, payout idempotente
- `backend/admin/router.py` — fee al aprobar claim, chargebacks, statement, policy, audit
- `backend/social/partners.py` — financial_statement en `/partners/me`
- `backend/refunds/router.py` — anti-doble refund por `fact_refunds`
- `backend/.env.example` — nuevas vars

### Docs
- `docs/BUSINESS_MODEL_PLATFORM.md`
- `docs/OPEN_DEPENDENCIES.md`
- `docs/INFORME_FINAL_PLATAFORMA.md` (este)
- Actualización `docs/FASE_DINERO_LEDGER.md`

### Migraciones Pinot
**Ninguna schema nueva obligatoria** — se reutiliza `fact_partner_ledger` con nuevos `entry_type`. No se recrearon tablas destructivamente.

## 23–26. Pruebas / errores

Ejecutado: `python tests/test_financial_integrity.py` (ver resultado en sesión).

Errores encontrados en implementación: uso incorrecto de `admin_id` en approve claim → **corregido**.

## 27–28. Dependencias externas y decisiones pendientes

Ver `docs/OPEN_DEPENDENCIES.md` (D01–D14).

## 29. Riesgos

Fraude/CB, refund abuse, liquidez payouts, competencia Steam/Epic, vacío de catálogo, compliance fiscal, Kafka/Pinot eventual consistency (mitigado con cache ledger), secretos en `.env`.

## 30. Siguiente evolución recomendada

1. Cerrar D04–D06 (legal/fiscal/PSP) antes de dinero real.
2. Playtime-aware refunds + Stripe refund to source.
3. Webhook disputes → `POST` interno chargeback.
4. DLC catalog + entitlements.
5. Partner monthly PDF/CSV export (ya hay statement JSON).
6. Marketplace solo con anti-fraude/AML.

---

**Objetivo alcanzado:** de “proyecto de software” a **base tecnológica + empresarial documentada** de una plataforma de distribución, con integridad financiera reforzada y sin fingir integraciones/credenciales inexistentes.
