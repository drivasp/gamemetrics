# Auditoría GameMetrics (solo lectura)

| Campo | Valor |
|-------|--------|
| **Repositorio** | https://github.com/drivasp/gamemetrics.git |
| **Commit base** | `ee22a261896024b4a2c8c51e8382c0b8a21b4933` — *Finalize financial ledger and E2E audit* |
| **Fecha del informe** | 2026-08-12 |
| **Alcance** | Inventario verificado por lectura de código. **Sin cambios de implementación.** |
| **Artefacto** | Este archivo únicamente |

Fuentes Steamworks usadas (oficiales):

- https://partner.steamgames.com/doc/features
- https://partner.steamgames.com/doc/features/achievements
- https://partner.steamgames.com/doc/api/ISteamUserStats
- https://partner.steamgames.com/doc/store/application/dlc

---

## 1. Resumen ejecutivo

GameMetrics es una plataforma tipo tienda + partner portal + ops analytics sobre **Angular + FastAPI + Kafka + Pinot + SQLite ledger + MinIO**, con **24 routers activos** montados en `backend/main.py` (coinciden con el punto de partida: auth, tienda, wishlist, carrito, biblioteca, reseñas, dimensiones, empresa, wallet, checkout, coupons, refunds, gifts, launcher, social, community, events, alerts, saves, regional/locale, admin, reports, tax, marketplace).

**Qué tiene hoy (verificado):** flujo store → cart → checkout (sandbox/wallet/Stripe) → library; wishlist/alerts; wallet con ledger durable; partner register/claims/builds/payouts/statement; admin GMV/auditoría; 20 reportes Pinot-backed; marketplace P2P **sandbox** (items/listings en memoria + dinero en SQLite); forums/family/friends/gifts/support; cloud saves API; achievements **lectura** vía launcher; fraud scoring en compra marketplace; tax engine configurable.

**Qué falta vs Steamworks (evidencia negativa):** **NO ENCONTRADO** en backend Python: leaderboards, workshop, curators, trading cards, DLC/bundles/demos/early access como entidades de catálogo, microtransactions in-game, inventory service Steam-like (el `/marketplace/inventory` es otro dominio), screenshots API de plataforma, matchmaking, DRM wrapper. Frontend: achievements = popup UI; no hay páginas dedicadas a workshop/leaderboards/curators.

**Top 3 riesgos (no tocar a la ligera el ledger):**

1. **Dual-write / gates en Pinot** para “ya pagado / ya reembolsado” mientras el SoT de wallet es SQLite → riesgo de carrera confirm+webhook y doble credit de refund (`refund_wallet_{uuid}`).
2. **Marketplace ownership en memoria de proceso** (`_ITEMS`/`_LISTINGS`) mientras el dinero sí es durable → reinicio o multi-réplica descuadra ownership vs saldo.
3. **RBAC de 3 roles** (`player|publisher|admin`) sin permisos granulares; `opsGuard` ≡ solo admin; JWT no es fuente de autorización de rol (se relee Pinot).

---

## 2. Inventario por módulo (Paso 1)

Convención de estado:

| Etiqueta | Significado |
|----------|-------------|
| ✅ COMPLETO | Backend + frontend conectado + datos Pinot/Kafka (o ledger) reales del flujo |
| 🟡 PARCIAL | Existe pero falta capa, cobertura o persistencia |
| ⚠️ SANDBOX | Funciona con mock/memoria/simulación no producción |
| 📦 ARCHIVADO | Solo en `_archivado` |
| ❌ AUSENTE | Sin evidencia en repo activo |

### 2.1 auth — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | `POST /auth/register`, `POST /auth/bootstrap-admin`, `POST /auth/login`, `GET|PUT /auth/profile`, `POST /auth/avatar` |
| **Datos** | Kafka/Pinot: `fact_users`, `fact_user_roles`, `fact_user_locale`, `fact_user_sessions`, `fact_user_sanctions` |
| **Frontend** | `auth.service.ts`, `auth-modal`, `profile`; guards |
| **Estado** | Funcional; roles solo 3 valores; bootstrap con secreto de entorno |
| **Evidencia** | `backend/auth/router.py`, `registro.py`, `roles.py`; `frontend/.../services/auth.service.ts` |

### 2.2 tienda (`/store`) — ✅ COMPLETO (catálogo)

| | |
|--|--|
| **Endpoints** | `GET /store/filters`, `cover*`, `featured`, `new-releases`, `popular`, `free-games`, `genres`, `games`, `games/{slug}` |
| **Datos** | Pinot `fact_videogames`, `fact_price_catalog`, `fact_promotions` (+ placements) |
| **Frontend** | `store.service.ts` + `store-home` / `store-catalog` / `store-game-detail` |
| **Estado** | ✅ lectura catálogo; **sin** modelo DLC/bundle/demo en backend (NO ENCONTRADO) |
| **Evidencia** | `backend/tienda/router.py`; `app.routes.ts` `store*` |

### 2.3 wishlist — ✅ COMPLETO

| | |
|--|--|
| **Endpoints** | `GET/POST/DELETE /user/wishlist…`, `GET .../check/{slug}` |
| **Datos** | `fact_wishlist` |
| **Frontend** | `wishlist.service.ts` (usado en detalle/perfil; **sin** ruta dedicada) |
| **Estado** | ✅ |
| **Evidencia** | `backend/wishlist/router.py` |

### 2.4 carrito — ✅ COMPLETO

| | |
|--|--|
| **Endpoints** | `GET/POST/DELETE /cart…` |
| **Datos** | `fact_cart`, cruce `fact_purchases` / precios |
| **Frontend** | `cart.service.ts` + `CartComponent` `/my-cart` |
| **Estado** | ✅ |
| **Evidencia** | `backend/carrito/router.py` |

### 2.5 biblioteca — ✅ COMPLETO

| | |
|--|--|
| **Endpoints** | `GET /library`, `GET /library/check/{slug}` |
| **Datos** | Pinot `fact_purchases` |
| **Frontend** | `library.service.ts` + `LibraryComponent`; integra launcher/saves/achievements |
| **Estado** | ✅ |
| **Evidencia** | `backend/biblioteca/router.py` |

### 2.6 resenas — ✅ COMPLETO

| | |
|--|--|
| **Endpoints** | `GET/POST/PUT/DELETE /reviews/{slug}`, `POST /reviews/votes/{id}` |
| **Datos** | `fact_reviews`, `fact_review_votes`, ownership via purchases |
| **Frontend** | `reviews.service.ts` (detalle de juego) |
| **Estado** | ✅ (verificadas por compra en lógica de backend; profundidad Steam-like no auditada end-to-end aquí) |
| **Evidencia** | `backend/resenas/router.py` |

### 2.7 dimensiones — ✅ COMPLETO (ops)

| | |
|--|--|
| **Endpoints** | `GET /api/dim/{plataformas|generos|desarrolladores|publicadores|esrb}[+ /count]` |
| **Datos** | dims Pinot |
| **Frontend** | `dimension.service.ts` + `DimensionesComponent` (`opsGuard`) |
| **Estado** | ✅ analytics interno |
| **Evidencia** | `backend/dimensiones/router.py` |

### 2.8 empresa — 🟡 PARCIAL / ⚠️ riesgo

| | |
|--|--|
| **Endpoints** | CRUD ` /empresa/{collection}/records` **sin auth en deps** |
| **Datos** | Kafka/Pinot `emp_records` |
| **Frontend** | `empresa.service.ts` + `EmpresaComponent` (`opsGuard` UI) |
| **Estado** | 🟡 UI admin-only pero API pública a nivel FastAPI |
| **Evidencia** | `backend/empresa/router.py` / `endpoints.py` |

### 2.9 wallet — ✅ COMPLETO (sandbox topup) / ⚠️ PSP

| | |
|--|--|
| **Endpoints** | `GET /wallet`, `GET /wallet/transactions`, `POST /wallet/topup` |
| **Datos** | **SoT SQLite** `financial_transactions`; Kafka `fact_user_wallets`, `fact_wallet_transactions` |
| **Frontend** | `wallet.service.ts` + `/my-wallet` |
| **Estado** | ✅ ledger durable; topup es sandbox (no PSP wallet real) |
| **Evidencia** | `backend/wallet/servicio.py`, `backend/ledger/sqlite_store.py` |

### 2.10 checkout — ✅ COMPLETO (sandbox) / ⚠️ Stripe opcional

| | |
|--|--|
| **Endpoints** | `POST /checkout`, `GET /checkout/confirm`, `POST /checkout/webhook` |
| **Datos** | orders/payments/purchases + partner ledger Kafka/Pinot; mirror durable partner/platform |
| **Frontend** | `LibraryService` / `PaymentComponent` |
| **Estado** | ✅ flujo comercial; webhook idempotency module **no cableado** (ver §5.C) |
| **Evidencia** | `backend/checkout/router.py`, `partner_ledger.py`, `saas_billing.py` |

### 2.11 coupons — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | `POST /coupons/validate` |
| **Datos** | `fact_coupons`, `fact_coupon_redemptions` |
| **Frontend** | vía payment/checkout (sin página coupons dedicada) |
| **Estado** | 🟡 API mínima |
| **Evidencia** | `backend/coupons/router.py` |

### 2.12 refunds — ✅ COMPLETO (reglas plataforma)

| | |
|--|--|
| **Endpoints** | `POST /refunds` |
| **Datos** | `fact_refunds`, purchases; reverse partner ledger + wallet credit |
| **Frontend** | llamado desde flujos library/E2E (sin página “mis refunds” dedicada encontrada) |
| **Estado** | ✅ con ventana 14d; riesgos de carrera Pinot (ver §5.C) |
| **Evidencia** | `backend/refunds/router.py` |

### 2.13 gifts — ✅ COMPLETO

| | |
|--|--|
| **Endpoints** | `POST /gifts`, inbox/sent, accept/decline |
| **Datos** | `fact_gifts`, purchases |
| **Frontend** | `gifts.service.ts` + `/my-gifts` |
| **Estado** | ✅ |
| **Evidencia** | `backend/gifts/router.py` |

### 2.14 launcher — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | achievements/me, library-status, game, updates, install/progress/uninstall, download token, verify, play start/end |
| **Datos** | builds, install_states, play_sessions, achievements, download_tokens |
| **Frontend** | `launcher.service.ts` embebido en **library** (no app launcher nativa) |
| **Estado** | 🟡 API tipo cliente; no es Steam client/DRM |
| **Evidencia** | `backend/launcher/router.py` |

### 2.15 social (+ partners) — ✅ COMPLETO (subset)

| | |
|--|--|
| **Endpoints** | `/friends*`, `/notifications*`, `/support*`, `/partners*` (register, games, builds, connect, saas, branding, featured, plans) |
| **Datos** | friendships, notifications, tickets, partner_accounts/games + SaaS topics |
| **Frontend** | `social.service.ts`; `/my-friends`, `/my-support`, `/my-partner` |
| **Estado** | ✅ partner portal usable; Stripe Connect opcional |
| **Evidencia** | `backend/social/router.py`, `partners.py` |

### 2.16 community — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | forums threads/posts; family create/invite/share; api-keys; search/log |
| **Datos** | forum_*, family_*, api_keys, search_queries |
| **Frontend** | forums en store-detail; family `/my-family`; api-keys en partner; **sin** hub community dedicado |
| **Estado** | 🟡 no es Community Hub Steam completo |
| **Evidencia** | `backend/community/*.py`; `community.service.ts` |

### 2.17 events — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | `POST /events` (telemetría usuario) |
| **Datos** | Kafka `fact_user_events` |
| **Frontend** | `events.service.ts` (payment/detail) |
| **Estado** | 🟡 logging; **NO** calendarios/announcements Steam |
| **Evidencia** | `backend/events/router.py` |

### 2.18 alerts — ✅ COMPLETO (price alerts)

| | |
|--|--|
| **Endpoints** | `GET/POST/DELETE /alerts` |
| **Datos** | `fact_wishlist_price_alerts` |
| **Frontend** | `alerts.service.ts` (detalle tienda) |
| **Estado** | ✅ |
| **Evidencia** | `backend/alerts/router.py` |

### 2.19 saves — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | `GET/PUT/DELETE /saves/{product_id}[/{slot}]` |
| **Datos** | `fact_cloud_saves` |
| **Frontend** | vía `launcher.service` + library |
| **Estado** | 🟡 API cloud-save; no Auto-Cloud Steam client |
| **Evidencia** | `backend/saves/router.py` |

### 2.20 regional (`locale_router`) — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | `GET /locale/countries`, `GET /locale/me`, `PUT /locale/me` (**403 país bloqueado**) |
| **Datos** | `fact_user_locale` |
| **Frontend** | `locale.service.ts` |
| **Estado** | 🟡 locale fijo post-registro |
| **Evidencia** | `backend/regional/router.py` |

### 2.21 admin — ✅ COMPLETO (ops admin)

| | |
|--|--|
| **Endpoints** | health, gmv, dashboard, set role, payouts, claims approve/reject, chargebacks, statement, finance policy/audit |
| **Datos** | partners + ledger helpers + audit |
| **Frontend** | `AdminComponent` HttpClient directo `/admin/*` |
| **Estado** | ✅ |
| **Evidencia** | `backend/admin/router.py`; `admin.component.ts` |

### 2.22 reports — ✅ COMPLETO (ops) / 🟡 comercial

| | |
|--|--|
| **Endpoints** | `GET /reports/catalog`, `/view/{code}`, `/export.csv` — **admin only** |
| **Datos** | Pinot + payouts + ETL status (S06) |
| **Frontend** | `/reports`, `/reports/:code` (`opsGuard`) |
| **Estado** | ✅ 20 códigos reales; faltan embudos/drill-down Steam Sales site |
| **Evidencia** | `backend/reports/catalog.py`, `service.py`; `reports.service.ts` |

### 2.23 tax — 🟡 PARCIAL

| | |
|--|--|
| **Endpoints** | rules, jurisdictions, quote, audit (admin) |
| **Datos** | motor local / `tax_rules.json` (no Pinot) |
| **Frontend** | vía checkout/cart (no UI tax dedicada) |
| **Estado** | 🟡 motor configurable; no Avalara/Vertex |
| **Evidencia** | `backend/tax/router.py`, `engine.py` |

### 2.24 marketplace — ⚠️ SANDBOX

| | |
|--|--|
| **Endpoints** | fees (público), listings, inventory, history, items, listings, cancel, buy |
| **Datos** | **Memoria** items/listings/txs; dinero → SQLite; Kafka `market_*` |
| **Frontend** | `MarketplaceComponent` `/my-marketplace` |
| **Estado** | ⚠️ no producción multi-instancia |
| **Evidencia** | `backend/marketplace/service.py` líneas `_ITEMS`/`_LISTINGS` |

### Módulos auxiliares (no son “los 24 routers” pero relevantes)

| Módulo | Estado | Evidencia |
|--------|--------|-----------|
| `ledger/` | ✅ SoT dinero | `backend/ledger/sqlite_store.py` |
| `fraud/` | 🟡 usado en market buy | `backend/fraud/service.py` |
| `security/` rate limit | 🟡 middleware | `backend/security/` |

### Confirmación punto de partida

| Afirmación previa | Veredicto |
|-------------------|-----------|
| 24 routers en FastAPI | **CONFIRMADO** (`main.py` includes) |
| Rutas Angular listadas | **CONFIRMADO** (`app.routes.ts`) |
| Achievements FE sin leaderboards/workshop/… backend | **CONFIRMADO** (grep backend sin matches; achievements en launcher) |
| `_archivado` con restos Java/PocketBase | **CONFIRMADO** (`pom.xml`, `cliente_pocketbase.py`) |
| Stack Angular+FastAPI+Kafka+Pinot+Docker+MinIO | **CONFIRMADO** (compose + código) |
| Finanzas estabilizadas | **CONFIRMADO** presencia ledger/revenue_share/refunds/payouts; **NO** implica “libre de riesgo de carrera” |

---

## 3. Análisis de archivados (Paso 2)

| Archivado | ¿Por qué parece archivado? | ¿Activo lo reemplaza? | Lógica perdida? | Recomendación |
|-----------|----------------------------|------------------------|-----------------|---------------|
| **alerts** | Snapshot viejo del mismo módulo | Sí, `backend/alerts/` | No aparente | **BORRAR DEFINITIVO** tras diff opcional |
| **checkout** | Pre-tax/partner/ledger | Activo **superset** | No; activo más rico | **BORRAR** (conservar solo si hay diff histórico de negocio) |
| **community** | Copia paralela | Sí | No aparente | **BORRAR** |
| **coupons** | Copia | Sí | No aparente | **BORRAR** |
| **dashboard** | API Java/analytics `/api/dashboard` | **No** paquete homónimo; absorbido por **reports** C04–C07 + FE dashboard | Queries por año/género/plataforma/ESRB/top — parcialmente en reports | **MIGRAR LÓGICA** si falta algún corte; luego **BORRAR** |
| **events** | Copia | Sí | No | **BORRAR** |
| **games** | Catálogo legacy `/api/games` | Reemplazado por **tienda**/Pinot | Endpoints list/count/get viejos | **BORRAR** |
| **gifts** | Copia | Sí | No | **BORRAR** |
| **launcher** | Versión menor | Activo creció | Posible detalle menor — verificar diff antes de borrar | **DEJAR** hasta diff; luego **BORRAR** |
| **refunds** | Sin partner reverse / prior-refund | Activo superior | No; activo gana | **BORRAR** |
| **social** | Partners más delgados | Activo + `partner_game_claims` | No | **BORRAR** |
| **wallet** | SoT era Pinot | Activo = **SQLite ledger** | **No reactivar** el SoT Pinot | **BORRAR** (peligroso reactivar) |
| **cliente_pocketbase.py** | Auth/datos PB | JWT + Pinot/Kafka | Solo si alguien aún usa PB externo — **NO ENCONTRADO** en activo | **BORRAR** |
| **pom.xml** | Backend Java Spring | Python FastAPI | Artefacto legacy | **BORRAR** |

---

## 4. Tabla comparativa vs Steam (Paso 3)

Referencia Steam: documentación Steamworks citada arriba. Donde no se abrió un doc específico en esta auditoría, se marca *no verificado en docs oficiales en esta pasada* aunque la capacidad sea pública en Steam.

| Capacidad | ¿Existe en GameMetrics? | Evidencia | Estado | ¿Steam lo documenta? | Complejidad |
|-----------|-------------------------|-----------|--------|----------------------|-------------|
| Store | Sí | `tienda/`, rutas `store*` | ✅ | Sí (Store Presence / features) | — |
| Search | Parcial | `GET /store/games` + `POST /search/log` | 🟡 | no verificado doc search específica aquí | MEDIA |
| Discovery/recomendaciones | Parcial | featured/popular/new/free | 🟡 | no verificado algoritmos Steam | ALTA |
| Wishlist | Sí | `wishlist/` | ✅ | no verificado doc específica aquí | — |
| Cart | Sí | `carrito/` | ✅ | no verificado | — |
| Checkout | Sí | `checkout/` | ⚠️ sandbox/Stripe | Microtransactions/store checkout docs existen; PSP propio ≠ Steam | MEDIA (PSP prod) |
| Wallet | Sí | `wallet/` + ledger | ⚠️ topup sandbox | Steam Wallet (producto Steam; no verificado API partner completa aquí) | ALTA (regulado) |
| Library | Sí | `biblioteca/` | ✅ | Ownership docs Steamworks | — |
| Launcher | Parcial | `launcher/` API | 🟡 | Steam client/DRM documentados | MUY ALTA |
| DLC | **NO ENCONTRADO** | grep backend sin dlc | ❌ | **Sí** https://partner.steamgames.com/doc/store/application/dlc | ALTA |
| Bundles | **NO ENCONTRADO** (solo copy dashboard) | FE dashboard texto | ❌ | no verificado doc bundles aquí | ALTA |
| Editions | **NO ENCONTRADO** | — | ❌ | no verificado | ALTA |
| Demos | **NO ENCONTRADO** como producto | — | ❌ | Steam Keys menciona demos en features | MEDIA |
| Early Access | **NO ENCONTRADO** | — | ❌ | no verificado | MEDIA |
| Achievements | Parcial | `GET /launcher/achievements/me` + popup FE | 🟡 | **Sí** features/achievements + ISteamUserStats | MEDIA |
| Leaderboards | **NO ENCONTRADO** | grep | ❌ | **Sí** Steam Leaderboards | MEDIA |
| Cloud Saves | Parcial | `saves/` | 🟡 | **Sí** Steam Cloud | MEDIA |
| Inventory (Steam Inventory Service) | **NO** (sí market inventory) | marketplace ≠ Steam Inventory | ❌ / ⚠️ | **Sí** Inventory Service | ALTA |
| Marketplace | Sí sandbox | `marketplace/` | ⚠️ | Community Market (no verificado API partner aquí) | ALTA |
| Microtransactions | **NO ENCONTRADO** | — | ❌ | **Sí** Microtransactions en features | ALTA |
| Workshop | **NO ENCONTRADO** | — | ❌ | **Sí** Steam Workshop | MUY ALTA |
| Community Hub | Parcial forums | `community/forums` | 🟡 | Community (no hub completo verificado) | ALTA |
| Guides | **NO ENCONTRADO** | — | ❌ | no verificado | MEDIA |
| Screenshots/Artwork | Parcial UI media RAWG | `store.service` screenshots | 🟡 | **Sí** Steam Screenshots | MEDIA |
| Events (calendario) | No (solo telemetry POST) | `events/` | 🟡/❌ | Game Notifications / events (parcialmente documentados) | MEDIA |
| Announcements | **NO ENCONTRADO** | — | ❌ | no verificado | BAJA–MEDIA |
| Notifications | Sí | `/notifications` | ✅ | Game Notifications documentadas | — |
| Friends | Sí | `/friends` | ✅ | Friends/Rich Presence docs | MEDIA (rich presence) |
| Family Sharing | Parcial | `/family*` | 🟡 | no verificado doc Family Sharing oficial en esta pasada | ALTA |
| Gifts | Sí | `gifts/` | ✅ | no verificado | — |
| Reviews verificadas | Sí (compra) | `resenas/` | ✅ | no verificado | — |
| Curators | **NO ENCONTRADO** | — | ❌ | no verificado | MEDIA |
| Trading Cards | **NO ENCONTRADO** | — | ❌ | **Sí** (features: set up in portal) | MEDIA |
| Developer Portal | Parcial partner | `/my-partner`, builds | 🟡 | Steamworks partner site | ALTA |
| Publisher Portal | Parcial | partners + admin | 🟡 | Steamworks | ALTA |
| Analytics/Reportes | Sí 20 reports | `reports/` | 🟡 vs Sales Reporting Steam | Sales reports (no abierto en detalle aquí) | ALTA |
| Traffic reporting | Parcial | reportes catálogo/semana | 🟡 | no verificado | ALTA |
| Finance dashboard | Sí | admin + partner statement | ✅/🟡 | Partner financial (no verificado doc) | — (**proteger**) |
| Revenue Share | Sí | `revenue_share.py` | ✅ política plataforma | Steam revenue share (industria; tiers documentados en vuestros docs, no re-verificados aquí) | — (**proteger**) |
| Refunds | Sí | `refunds/` | ✅ | Política Steam store (no doc partner abierta aquí) | — (**proteger**) |
| Payouts | Sí | admin/partner payouts | ⚠️ Stripe Connect opcional | no verificado | MEDIA |
| Fraud detection | Parcial | `fraud/service.py` | 🟡 | Anti-cheat docs ≠ payment fraud | ALTA |
| Moderation | Parcial sanctions table | `fact_user_sanctions` referenciada en auth | 🟡 | Community moderation (no verificado) | MEDIA |
| RBAC | Parcial 3 roles | `auth/roles.py` | 🟡 | no aplica 1:1 Steam | MEDIA |
| Audit log | Sí | `financial_audit` + `/admin/finance/audit` | ✅ | no verificado | — |

---

## 5. Análisis de RBAC, Reportes y Finanzas (Paso 4)

### A) RBAC

**Qué existe (evidencia):**

- Roles canónicos: `player | publisher | admin` — `backend/auth/roles.py`.
- Persistencia: Pinot `fact_user_roles` + cache 300s; escritura Kafka.
- Auth API: `require_token`, `require_roles(*roles)` en `shared/auth_deps.py`. **NO existe** `require_admin` como símbolo; se usa `require_roles(..., "admin")`.
- Autorización de rol **no confía en el claim JWT**: relee Pinot en cada `require_roles`.
- Frontend: `authGuard` (logueado), `adminGuard` / `opsGuard` → **solo `admin`**. Publisher no ve reports/ops.
- Elevación: register→player; `/partners/register`→publisher; admin `PUT /admin/users/{id}/role`; `bootstrap-admin` + secreto.

**Qué falta para RBAC profesional:**

- Permisos granulares (scopes: `finance.read`, `payout.execute`, `moderation.ban`, etc.).
- Separación ops analyst vs finance vs support vs super-admin.
- Bindings org/partner (multi-user por estudio).
- Auditoría de cambios de permiso más allá de financial audit.
- Alineación JWT↔UI tras cambio de rol (hoy hint de re-login).
- Protección API `empresa` (hoy sin auth en router).

### B) Reportes / dashboards

**Qué existe:**

- **20 códigos** GM-S01…S13 + GM-C01…C07 en `backend/reports/catalog.py`.
- Backend y UI **admin-only**.
- Datos: mayoría `pinot_query` sobre facts reales; C01–C03 vía dashboard/earnings; S06 HTTP ETL status.
- **No** se hallaron KPIs de ventas inventados hardcodeados; hay constantes de política (ventana refund 14d, límites LIMIT, semana 1–17).

**Métricas hoy (títulos catalog):** cola claims, liquidaciones, tickets, empleados/contratos (empresa), ETL, marketing, catálogo distribución, featured, compras jugadores, elegibles refund, juegos por estudio, liquidaciones estudio, resumen económico, ganancias estudio, desempeño estudio, volumen/género/plataforma semanal, top 10 rating.

**Qué falta para dashboards comerciales tipo Steam Sales:**

- Embudos (impresiones→wishlist→cart→purchase).
- Comparativas periodo-over-periodo, cohortes, segmentación geográfica/precio.
- Drill-down interactivo (hoy filtros limitados: status, partner_id, week).
- Traffic storefront / conversion rates.
- Publisher self-serve analytics (hoy reports son admin/ops).

### C) Integridad financiera (proteger lo existente)

**Protecciones ya presentes:**

| Mecanismo | Dónde |
|-----------|--------|
| `UNIQUE(idempotency_key)` + tx SQLite | `ledger/sqlite_store.py` |
| Wallet balance = SUM posted | `wallet/servicio.py` |
| Checkout Idempotency-Key / derived key + Pinot completed payment | `checkout/router.py` |
| `order_already_paid` antes de fulfill | `checkout/servicio.py` |
| Partner sale/refund IDs deterministas + durable keys | `partner_ledger.py` |
| Marketplace keys `mkt_*_{listing}_{key}` | `marketplace/service.py` |
| Refund: flag refunded + prior refund Pinot + ventana | `refunds/router.py` |
| Payout soft-idempotency por reference + Stripe idempotency_key | `partner_payouts.py` |
| Fees públicos puros | `marketplace/fees_calc.py` + router |

**Riesgos si se añaden features encima (sin proponer cambios):**

1. Confirm Stripe + webhook concurrentes con lag Pinot → doble fulfill/purchase.
2. `webhook_idempotency.py` **existe pero no se importa en** `checkout/router.py` webhook.
3. Refund: `refund_wallet_{refund_id}` con UUID nuevo por request → carrera puede doble-acreditar wallet aunque partner durable sea estable.
4. Wallet sin idempotency_key → auto UUID → no retry-safe.
5. Marketplace: ownership memoria vs dinero durable.
6. Fallos `durable sale skip` solo `print` → descuadre partner SQLite vs Kafka ownership.
7. Payout sin key/reference → riesgo doble transferencia.
8. Cualquier nuevo flujo que lea “balance” desde Pinot en vez de SQLite reintroduce el modelo viejo archivado.

**Recomendación de gobernanza (no implementación):** tratar `ledger/`, `wallet/servicio.py`, `partner_ledger.py`, `refunds/`, `checkout` fulfill y `marketplace` buy como **zona restringida**; cualquier feature nueva debe declarar su `idempotency_key` estable y no usar Pinot como SoT monetario.

---

## 6. Plan de implementación recomendado (Paso 5)

Solo planificación. Orden por dependencias y riesgo al ledger.

### Bloque 0 — Higiene y seguridad base (BAJA–MEDIA)
- Diff y limpieza `_archivado` (empezar por wallet/checkout viejos peligrosos).
- Cerrar auth en `empresa` API; alinear secrets/bootstrap en prod.
- Documentar zona prohibida ledger.
- **Toca:** empresa, archivados. **Ledger riesgo:** bajo si no se toca dinero.
- **Pruebas:** auth empresa 401; smoke OpenAPI; no regresiones store.

### Bloque 1 — Catálogo comercial (DLC/editions/demos) (ALTA)
- Modelo producto (parent app, DLC app, ownership checks) inspirado en Steam DLC docs.
- UI store detalle + library ownership.
- **Toca:** tienda, biblioteca, checkout line items. **Ledger riesgo:** MEDIO (nuevas líneas de venta deben reusar `record_sale_ledger` + durable keys).
- **Reutilizar:** purchases, partner attribution.
- **Pruebas:** financial integrity, compra+refund DLC, E2E ownership.

### Bloque 2 — Persistencia marketplace (ALTA, después de 1 o en paralelo cuidadoso)
- Durable ownership/listings (no solo memoria) **sin** reescribir fórmulas de fee.
- **Toca:** marketplace. **Ledger riesgo:** ALTO — no cambiar posting buyer/seller/fees sin tests de idempotencia.
- **Pruebas:** audit-cierre market, doble compra, restart container ownership.

### Bloque 3 — RBAC profesional (MEDIA)
- Permisos granulares + roles ops/finance/support; publisher org members.
- **Toca:** auth, admin, reports guards, partners. **Ledger riesgo:** bajo si solo authz.
- **Pruebas:** fase0-roles, admin 403, publisher no ve reports.

### Bloque 4 — Player platform features (MEDIA–ALTA)
- Leaderboards + achievements write API (Steam ISteamUserStats como referencia de producto).
- Cloud saves hardening; notifications/announcements.
- **Toca:** launcher, saves, community. **Ledger riesgo:** ninguno si no mezclan IAP.
- **Pruebas:** library achievements, saves roundtrip.

### Bloque 5 — Analytics comerciales (ALTA)
- Embudos, PoP, publisher self-serve reports.
- **Toca:** reports, Pinot schemas, partner UI. **Ledger riesgo:** solo lectura — no mutar ledger.
- **Pruebas:** catalog 20 + nuevos códigos; no cambiar C01–C03 aggregations sin golden files.

### Bloque 6 — UGC / Workshop / Inventory Steam-like (MUY ALTA)
- Solo tras marketplace durable y authz.
- **Toca:** nuevo dominio + MinIO. **Ledger riesgo:** alto si hay ventas de items.
- **Pruebas:** aislamiento financiero + fraud.

### Bloque 7 — PSP / Wallet real / Connect prod (MUY ALTA, legal)
- Credenciales Stripe live, webhook event-id store, compliance.
- **Toca:** checkout webhook, wallet topup. **Ledger riesgo:** MÁXIMO.
- **Pruebas:** idempotencia webhook, payout fail sandbox, no doble fulfill.

**Orden sugerido:** 0 → 3 (rápido win seguridad) → 1 → 2 → 4 → 5 → 6/7 según negocio.

---

## 7. Suposiciones y no verificados

1. **No se ejecutó** la app, tests, migraciones ni Docker en esta auditoría (mandato de solo lectura). Estados “funciona” se inferen del código + commits previos documentados, no de una corrida nueva.
2. **Steam:** solo se consultaron páginas oficiales listadas. Capacidades Steam marcadas “no verificado en docs oficiales en esta pasada” no deben tomarse como “Steam no lo tiene”.
3. **Angular “17”:** no se releyó `package.json` en esta pasada; se acepta el stack declarado por el usuario salvo contradicción. *(No verificado versión exacta aquí.)*
4. **Reviews “verificadas”:** se asume cruce con `fact_purchases` por patrones del módulo; no se trazó cada rama condicional línea a línea.
5. Diff línea-a-línea `_archivado` vs activo **no** se ejecutó con `diff` completo; recomendaciones de borrado asumen supersets observados.
6. Multi-región Pinot / lag real en prod **no medido**.
7. Contenido de MinIO builds y políticas de retención **no auditados en profundidad**.
8. `fraud/` y rate limit: existencia confirmada; efectividad offline no evaluada.
9. El punto de partida “24 routers” cuenta includes de `main.py`; partners viven **dentro** de social, no como include separado — coherente con 24 módulos de primer nivel.
10. Cualquier afirmación de “Steam revenue % exacto vigente” **no** se revalidó contra partner docs en esta pasada (usar `docs/` internos del repo como política GameMetrics).

---

*Fin del informe. Ningún otro archivo fue modificado por mandato de esta tarea.*
