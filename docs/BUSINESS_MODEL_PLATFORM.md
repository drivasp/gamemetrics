# Modelo de negocio y arquitectura — GameMetrics Platform

Documento de consultoría empresarial. Base para Business Plan, pitch, modelo financiero y arquitectura.
Última actualización: 2026-08-12.

---

## 1. Resumen ejecutivo

**GameMetrics** es una plataforma digital de distribución y comercialización de videojuegos (marketplace de dos lados: jugadores ↔ desarrolladores/publishers), inspirada en Steam/Epic pero no una copia.

**Estado técnico actual:** el núcleo económico ya opera en demo (checkout, impuestos regionales, wallet, refunds, ledger 70/30, claims, payouts, SaaS featured, 20 informes ETL→Pinot).

**Recomendación de modelo (empresa nueva):**
- Take rate **30% fijo** al inicio (`REVENUE_SHARE_MODE=flat`, publisher share 70%).
- Tarifa de publicación **$100 recuperable a $1.000 AGR** (alineada a Steam Direct oficial).
- Featured/SaaS como segunda línea B2B.
- Wallet de jugador (ya existe) con ledger de movimientos.
- **No** Community Market ni Game Pass en MVP.
- Tramos Steam-like (`steam_tiers`) opcionales vía env cuando un título lo justifique.

---

## 2. Investigación Steam — fuentes y clasificación de datos

### 2.1 Datos oficiales (Valve / Steamworks / Steam Store)

| Tema | Dato | Fuente |
|------|------|--------|
| Steam Direct Fee | **$100 USD** por app; no reembolsable; **recoup** tras **$1.000** Adjusted Gross Revenue; no pagable con Wallet; VAT/GST pueden aplicar | [Steam Direct Fee](https://partner.steamgames.com/doc/gettingstarted/appfee) |
| Pagos a partners | Mensual; mínimo **$100**; EFT (ACH US / SWIFT USD); pago ~**30 días** después del mes de venta | [Reporting and Payments](https://partner.steamgames.com/doc/finance/payments_salesreporting) |
| Reportes | Sales & Activations (casi real-time, **sin** deducciones); monthly report **con** refunds/chargebacks/taxes | Idem |
| Precios | Partners fijan precios; **37 monedas**; 4 region groups; herramientas de conversión PPP/FX | [Pricing](https://partner.steamgames.com/doc/store/pricing) |
| Refunds jugadores | ~14 días + &lt;2h playtime (juegos); política pública | [Steam Refunds](https://store.steampowered.com/steam_refunds/) |

### 2.2 Datos de terceros / industria (no inventados; no tratados como “API oficial”)

| Tema | Dato reportado | Clasificación |
|------|----------------|---------------|
| Revenue share escalonado | 30% ≤$10M · 25% $10–50M · 20% &gt;$50M lifetime **por juego**; no retroactivo | Anuncio Valve ~2018 + guías industria; **confirmar en Steamworks Financials**. En código: `REVENUE_SHARE_MODE=steam_tiers` |
| Community Market fee | Históricamente ~15% total (suele citarse 5% Valve + 10% juego) | **Valve no publica un % único limpio en la página Steamworks consultada**; tratar como terciario hasta confirmar en UI/SSA |
| Margen neto Valve | No público | **Valve no publica oficialmente este dato** |

### 2.3 Epic (benchmark oficial)

- 100% del primer **$1M** net revenue **por producto por año** (desde Jun 2025); luego **88%/12%**. Fuente: [Epic Distribution](https://store.epicgames.com/en-US/distribution).

---

## 3. Steam como plataforma B2B2C

Steam no “solo cobra 30%”. Opera un ecosistema:

```
Developers/Publishers  ←→  Steam (infra + store + pagos + comunidad)  ←→  Players
         ↑                              ↑                                      ↑
    distribución, tools            take rate, wallet,                catálogo, biblioteca,
    analytics, discovery           market fees, Direct fee           social, refunds
```

**Efecto de red:** más jugadores → más atractivo para devs → más juegos → más jugadores.

---

## 4. Participantes (mapa)

| Actor | Qué hace | Qué recibe | Qué paga | Riesgos | Incentivo |
|-------|----------|------------|----------|---------|-----------|
| Valve/Steam | Plataforma, CDN, pagos, discovery | Take rate, fees, market, Direct fee | Infra, soporte, fraude | Competencia, regulación | Escala + lock-in biblioteca |
| Developer | Crea juegos | 70–80% AGR (según tramo) | Direct fee, marketing | Refunds, chargebacks, descubribilidad | Audiencia + tools |
| Publisher | Comercializa / asume pago | Revenue share pactado | Steam + dev deals | IP, cashflow | Escala multi-SKU |
| Jugador | Compra / juega | Licencia digital, servicios | Precio + impuestos | Account bans, region lock | Catálogo + amigos |
| PSP / bancos | Procesan dinero | Fees % + fijos | — | Fraude | Volumen |
| Autoridad fiscal | Regula | VAT/GST/sales tax / withholdings | — | Compliance | Cumplimiento |
| Infra (cloud/CDN) | Hosting | Fees | — | Outages | Contrato |

---

## 5. Flujo de dinero (Steam conceptual → GameMetrics)

```
Jugador paga (precio + tax display según jurisdicción)
  → PSP
  → Steam/GM recoge tax (obligación jurídica: revisar con abogado/contador)
  → Refunds / chargebacks restan de AGR
  → Revenue share sobre ingreso ajustado (NO sobre tax)
  → Plataforma fee | Publisher net
  → Hold / mes + umbral
  → Payout EFT
```

**GameMetrics implementado:** `fact_order_taxes` + `fact_partner_ledger` (gross pre-tax) + refunds + chargebacks (admin) + payouts + Direct fee/recoup.

---

## 6. Ejemplos financieros

### Supuestos comunes (marcados)
- Take flat 30% (modo default GameMetrics).
- Impuestos: **excluídos del split** (como en nuestro ledger).
- Refunds/chargebacks: 0 salvo donde se indique (**supuesto**).

| Caso | Gross | Fee 30% | Publisher 70% |
|------|-------|---------|---------------|
| Juego $10 | 10 | 3 | 7 |
| Juego $20 | 20 | 6 | 14 |
| Juego $50 | 50 | 15 | 35 |
| $1.000 ventas | 1000 | 300 | 700 |
| $100.000 | 100000 | 30000 | 70000 |
| $1.000.000 | 1e6 | 300000 | 700000 |
| $10.000.000 | 1e7 | 3e6 | 7e6 |

### Steam tiers (industria; modo `steam_tiers`)

| Lifetime AGR | Fee plataforma (progresivo) | Publisher |
|--------------|----------------------------|-----------|
| $10M | $3.0M (todo @30%) | $7.0M |
| $50M | $3M + $10M = $13M | $37M |
| $60M | $13M + $2M = $15M | $45M |

Ejemplo con supuestos de ajuste ($1.000 ventas, 5% refunds, 0 CB):
- AGR = 950 → fee 285 → publisher 665.

---

## 7. Modelo recomendado GameMetrics

### Ingresos
1. **Comisión ventas** (30%) — core.
2. **Publication fee** ($100, recoup $1k) — calidad/spam filter.
3. **Featured/SaaS** — ya existe.
4. **DLC/IAP** — misma comisión cuando exista catálogo (parcial).
5. Marketplace secundario — **diferido**.
6. Suscripción jugadores — **no** en MVP (quema margen).

### Costos
- Fijos: ingeniería, producto, legal, cloud base.
- Variables: PSP fees, CDN egress, fraude/chargebacks, soporte, marketing adquisición.

### Unit economics (definiciones)
- **GMV** = suma precios juego pre-tax.
- **Take rate** = platform_fee / GMV.
- **AOV** = GMV / orders.
- **Refund rate** = refunds / sales.
- **Chargeback rate** = chargebacks / sales.
- **CAC / LTV** — **no instrumentados aún** (dependencia marketing attribution).

### Escenarios (supuestos — no proyecciones auditadas)

Supuestos: conversión compradora 5%, AOV $15, take 30%, costo var. pagos 3% GMV, opex fijo escalonado.

| Usuarios | Compradores/mes (sup.) | GMV/mes | Ingreso plataforma (~27% neto de PSP) | Nota |
|----------|------------------------|---------|----------------------------------------|------|
| 10k | 500 | $7.5k | ~$2k | MVP; no cubre nómina real |
| 100k | 5k | $75k | ~$20k | Startup |
| 1M | 50k | $750k | ~$200k | Escala |
| 10M | 500k | $7.5M | ~$2M | Gran plataforma |

**Punto de equilibrio (ejemplo conceptual):** si opex mensual = $50k y contribución ≈ 27% GMV → GMV break-even ≈ $50k / 0.27 ≈ **$185k/mes**. **Supuesto**; requiere presupuesto real de la empresa.

---

## 8. Arquitectura empresarial ↔ código

| Sistema | Estado | Módulo |
|---------|--------|--------|
| User / Auth / Roles | Hecho | `auth/`, `FASE0_ROLES` |
| Developer/Partner | Hecho | `social/partners.py` |
| Catalog / Store | Hecho | `tienda/` |
| Cart / Checkout / Orders | Hecho | `carrito/`, `checkout/` |
| Payments | Parcial (sandbox + Stripe opcional) | `checkout/router.py` |
| Wallet + tx ledger | Hecho | `wallet/` |
| Refunds | Hecho (14d; sin playtime limit) | `refunds/` |
| Chargebacks | **Nuevo** (admin API; webhook PSP pendiente) | `checkout/chargebacks.py` |
| Revenue share | Hecho + tiers opcionales | `checkout/revenue_share.py`, `partner_ledger.py` |
| Tax engine | Demo regional | `regional/`, `FASE3_*` |
| Payouts | Hecho (hold + min + Connect opcional) | `partner_payouts.py` |
| Direct fee | **Nuevo** | `checkout/direct_fee.py` |
| Statement | **Nuevo** | `financial_statement.py` |
| Audit | **Nuevo** (memoria) | `financial_audit.py` |
| Reports | Hecho (20) | `reports/` |
| Marketplace P2P | Falta | — |
| Fraud / CDN prod | Falta / parcial | MinIO builds |

---

## 9. Dependencias abiertas (NO inventadas)

1. **Legal:** jurisdicción societaria, ToS, licencia digital, DMCA/IP.
2. **Fiscal:** quién es merchant of record; VAT/OSS; withholdings a publishers no residentes.
3. **PSP:** contrato Stripe/Adyen; fees reales; disputes webhooks; KYC Connect.
4. **Monto exacto** publication fee / payout min prod ($100 Steam) — decisión board.
5. **Community Market** — regulación de bienes virtuales / AML.
6. **Credenciales** Stripe/RAWG — no hardcodear; `.env` local.

---

## 10. Ventaja competitiva (no genérica)

1. **Transparencia financiera:** statement tipo Steam monthly + 20 informes Pinot desde día 1.
2. **Precios/impuestos LATAM** como producto (no afterthought).
3. **Fee y hold configurables** sin opacidad.
4. **Payouts con hold alineado a refunds** (cashflow sano).
5. No pelear exclusivas AAA al inicio: **indies LATAM + herramientas B2B** (claims, featured, builds).

---

## 11. APIs nuevas / relevantes

- `GET /admin/finance/policy` — fees, modos, ejemplos tiers.
- `GET /admin/finance/audit` — auditoría en memoria.
- `POST /admin/chargebacks` — registra CB idempotente.
- `GET /admin/partners/{id}/statement` — estado financiero.
- `GET /partners/me` → `financial_statement` + `publication_fee_policy`.
- Al aprobar claim → asiento `direct_fee` (si `PUBLICATION_FEE_USD>0`).

---

## 12. Variables de entorno

Ver `backend/.env.example`: `REVENUE_SHARE_MODE`, `PUBLICATION_FEE_*`, `PAYOUT_*`, Stripe.

---

## 13. Pruebas financieras

```bash
cd backend
python tests/test_financial_integrity.py
```

Cubre: splits $10/$20/$50, tiers progresivos, IDs idempotentes, pipeline conceptual $1000.
