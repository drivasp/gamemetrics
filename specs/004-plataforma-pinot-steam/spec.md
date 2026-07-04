# Nivel Plataforma — GameMetrics Cloud (50 tablas Pinot)

## 1. Nombre del paquete
**004-plataforma-pinot-steam** — Plataforma de distribución digital tipo Steam usando únicamente Apache Pinot + Kafka.

## 2. Objetivo
Evolucionar GameMetrics S.A. de una demo analítica con tienda básica a una **plataforma de distribución digital completa** (catálogo, comercio, biblioteca, social, descargas, publisher B2B) manteniendo **Pinot como única base de datos** y Kafka como única vía de escritura transaccional (principios P1–P6).

## 3. Restricción arquitectónica
- **PERMITIDO:** Apache Pinot (OFFLINE + REALTIME), Apache Kafka, object storage (MinIO/filesystem) para binarios.
- **PROHIBIDO:** PostgreSQL, MySQL, MongoDB, Redis u otra base de datos relacional/documental.
- **Integridad referencial:** garantizada en la capa de aplicación (FastAPI), no en Pinot.

## 4. Resumen de tablas

| Tipo | Cantidad | Estado actual | Por crear |
|------|----------|---------------|-----------|
| OFFLINE | 10 | 6 | 4 |
| REALTIME | 40 | 3 | 37 |
| **TOTAL** | **50** | **9** | **41** |

## 5. Mapa de dominios

| Dominio | OFFLINE | REALTIME | Total |
|---------|---------|----------|-------|
| Catálogo y precios | 10 | 0 | 10 |
| Identidad y wallet | 0 | 4 | 4 |
| Comercio | 0 | 10 | 10 |
| Engagement | 0 | 5 | 5 |
| Social | 0 | 3 | 3 |
| Distribución digital | 0 | 4 | 4 |
| Publisher / B2B | 0 | 4 | 4 |
| Soporte y moderación | 0 | 2 | 2 |
| Comunidad extendida | 0 | 4 | 4 |
| Family sharing | 0 | 2 | 2 |
| Analytics comportamiento | 0 | 2 | 2 |
| **TOTAL** | **10** | **40** | **50** |

---

## 6. Catálogo completo de las 50 tablas

### A. OFFLINE — Catálogo y precios (10 tablas)

Cargadas vía ETL (Parquet → Pinot). Inmutables entre cargas semanales salvo recarga ETL.

| # | Tabla | PK | Estado | Descripción |
|---|-------|-----|--------|-------------|
| 01 | `fact_videogames` | `id` | ✅ Implementada | Catálogo base ~1.7M títulos. Campos: slug, name, rating, metacritic, genres, platforms, esrb_rating, released_ts, semana. |
| 02 | `dim_generos` | `dim_id` | ✅ Implementada | Dimensión géneros. |
| 03 | `dim_plataformas` | `dim_id` | ✅ Implementada | Dimensión plataformas. |
| 04 | `dim_desarrolladores` | `dim_id` | ✅ Implementada | Dimensión desarrolladores. |
| 05 | `dim_publicadores` | `dim_id` | ✅ Implementada | Dimensión publicadores. |
| 06 | `dim_esrb` | `dim_id` | ✅ Implementada | Dimensión clasificación ESRB. |
| 07 | `fact_game_products` | `product_id` | 🔲 Nueva | Producto vendible: juego base, edición, DLC, demo. Campos: product_id, parent_game_id, slug, name, product_type (base\|edition\|dlc\|demo), platform_targets, release_date, semana. |
| 08 | `fact_bundles` | `bundle_id` | 🔲 Nueva | Paquetes promocionales. Campos: bundle_id, name, slug, description, discount_pct, active, semana. |
| 09 | `fact_bundle_items` | `bundle_item_id` | 🔲 Nueva | Productos dentro de un bundle. Campos: bundle_item_id, bundle_id, product_id, semana. |
| 10 | `fact_price_catalog` | `price_id` | 🔲 Nueva | Precio por producto × región × moneda. Campos: price_id, product_id, region_code, currency, base_price, semana. |

---

### B. REALTIME — Identidad y wallet (4 tablas)

Topic Kafka = nombre de tabla. Upsert por PK + `deleteRecordColumn: deleted`.

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 11 | `fact_users` | `user_id` | `fact_users` | ✅ Implementada | Cuenta: email, password_hash, display_name, bio, avatar, deleted, created_at. |
| 12 | `fact_user_sessions` | `session_id` | `fact_user_sessions` | 🔲 Nueva | Sesiones activas. Campos: session_id, user_id, device_info, ip_hash, last_seen_at, expires_at, deleted. |
| 13 | `fact_user_wallets` | `user_id` | `fact_user_wallets` | 🔲 Nueva | Saldo wallet interno. Campos: user_id, balance, currency, updated_at, deleted. |
| 14 | `fact_wallet_transactions` | `tx_id` | `fact_wallet_transactions` | 🔲 Nueva | Movimientos wallet. Campos: tx_id, user_id, amount, tx_type (credit\|debit\|refund), idempotency_key, reference_id, created_at, deleted. |

---

### C. REALTIME — Comercio (10 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 15 | `fact_cart` | `cart_item_id` | `fact_cart` | 🔲 Nueva | `{user_id}_{product_id}`. Campos: game_slug, game_name, game_image, unit_price, quantity, added_at, deleted. |
| 16 | `fact_orders` | `order_id` | `fact_orders` | 🔲 Nueva | Cabecera de orden. Campos: order_id, user_id, total_amount, currency, status (pending\|paid\|failed\|refunded), created_at, deleted. |
| 17 | `fact_order_items` | `order_item_id` | `fact_order_items` | 🔲 Nueva | Líneas de orden. Campos: order_item_id, order_id, product_id, product_name, unit_price, quantity, deleted. |
| 18 | `fact_payments` | `payment_id` | `fact_payments` | 🔲 Nueva | Intentos de pago. Campos: payment_id, order_id, user_id, amount, provider (stripe\|wallet), stripe_session_id, idempotency_key, status, created_at, deleted. |
| 19 | `fact_purchases` | `purchase_id` | `fact_purchases` | 🔲 Nueva | Biblioteca del usuario (= licencia de uso). Campos: purchase_id, order_id, user_id, product_id, game_slug, game_name, game_image, amount, purchased_at, deleted. |
| 20 | `fact_refunds` | `refund_id` | `fact_refunds` | 🔲 Nueva | Devoluciones. Campos: refund_id, purchase_id, payment_id, user_id, amount, reason, status, created_at, deleted. |
| 21 | `fact_gifts` | `gift_id` | `fact_gifts` | 🔲 Nueva | Regalos entre usuarios. Campos: gift_id, sender_id, recipient_id, product_id, purchase_id, message, status, created_at, deleted. |
| 22 | `fact_coupons` | `coupon_code` | `fact_coupons` | 🔲 Nueva | Cupones activos. Campos: coupon_code, discount_type (pct\|fixed), discount_value, max_uses, uses_count, valid_from, valid_until, deleted. |
| 23 | `fact_coupon_redemptions` | `redemption_id` | `fact_coupon_redemptions` | 🔲 Nueva | Uso de cupón. Campos: redemption_id, coupon_code, user_id, order_id, discount_applied, created_at, deleted. |
| 24 | `fact_promotions` | `promo_id` | `fact_promotions` | 🔲 Nueva | Sales y promos. Campos: promo_id, name, product_id, discount_pct, start_at, end_at, active, deleted. |

---

### D. REALTIME — Engagement (5 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 25 | `fact_wishlist` | `wishlist_id` | `fact_wishlist` | ✅ Implementada | `{user_id}_{game_slug}`. Campos: user_id, game_slug, game_name, game_image, game_price, created_at, deleted. |
| 26 | `fact_wishlist_price_alerts` | `alert_id` | `fact_wishlist_price_alerts` | 🔲 Nueva | Alerta cuando baja el precio. Campos: alert_id, user_id, product_id, target_price, triggered, created_at, deleted. |
| 27 | `fact_reviews` | `review_id` | `fact_reviews` | 🔲 Nueva | `{user_id}_{product_id}`. Campos: user_id, product_id, game_slug, rating (1-5), comment, created_at, updated_at, deleted. |
| 28 | `fact_review_votes` | `vote_id` | `fact_review_votes` | 🔲 Nueva | Votos útil/no útil. Campos: vote_id, review_id, voter_id, helpful (bool), created_at, deleted. |
| 29 | `fact_user_events` | `event_id` | `fact_user_events` | 🔲 Nueva | Funnel y comportamiento. Campos: event_id, user_id, event_type, product_id, metadata_json, created_at. |

---

### E. REALTIME — Social (3 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 30 | `fact_friendships` | `friendship_id` | `fact_friendships` | 🔲 Nueva | Relaciones. Campos: friendship_id, user_id, friend_id, status (pending\|accepted\|blocked), created_at, deleted. |
| 31 | `fact_user_activity` | `activity_id` | `fact_user_activity` | 🔲 Nueva | Feed de actividad. Campos: activity_id, user_id, activity_type, reference_id, summary, created_at, deleted. |
| 32 | `fact_notifications` | `notification_id` | `fact_notifications` | 🔲 Nueva | Notificaciones in-app. Campos: notification_id, user_id, type, title, body, read, created_at, deleted. |

---

### F. REALTIME — Distribución digital (4 tablas)

Binarios en object storage; metadatos en Pinot.

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 33 | `fact_builds` | `build_id` | `fact_builds` | 🔲 Nueva | Versiones ejecutables. Campos: build_id, product_id, version, os (win\|mac\|linux), file_path, file_size_bytes, checksum, created_at, deleted. |
| 34 | `fact_download_tokens` | `token_id` | `fact_download_tokens` | 🔲 Nueva | URLs firmadas temporales. Campos: token_id, user_id, build_id, expires_at, used, created_at, deleted. |
| 35 | `fact_install_states` | `install_id` | `fact_install_states` | 🔲 Nueva | `{user_id}_{product_id}`. Campos: status (not_installed\|downloading\|installed\|updating), progress_pct, updated_at, deleted. |
| 36 | `fact_play_sessions` | `session_id` | `fact_play_sessions` | 🔲 Nueva | Tiempo jugado. Campos: session_id, user_id, product_id, started_at, ended_at, duration_minutes, deleted. |

---

### G. REALTIME — Publisher / B2B (4 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 37 | `emp_records` | `record_id` | `emp_records` | ✅ Implementada | 10 colecciones empresariales en estructura genérica (record_id, collection, data_json, deleted). |
| 38 | `fact_partner_accounts` | `partner_id` | `fact_partner_accounts` | 🔲 Nueva | Cuentas publisher B2B. Campos: partner_id, company_name, contact_email, revenue_share_pct, status, created_at, deleted. |
| 39 | `fact_partner_games` | `partner_game_id` | `fact_partner_games` | 🔲 Nueva | Juegos gestionados por partner. Campos: partner_game_id, partner_id, product_id, submission_status, created_at, deleted. |
| 40 | `fact_revenue_snapshots` | `snapshot_id` | `fact_revenue_snapshots` | 🔲 Nueva | Ventas agregadas por partner/producto. Campos: snapshot_id, partner_id, product_id, units_sold, gross_revenue, period_start, period_end, created_at. |

---

### H. REALTIME — Soporte y moderación (2 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 41 | `fact_support_tickets` | `ticket_id` | `fact_support_tickets` | 🔲 Nueva | Tickets de soporte. Campos: ticket_id, user_id, subject, body, status (open\|closed), priority, created_at, deleted. |
| 42 | `fact_user_sanctions` | `sanction_id` | `fact_user_sanctions` | 🔲 Nueva | Bans y moderación. Campos: sanction_id, user_id, sanction_type, reason, expires_at, created_at, deleted. |

---

### I. REALTIME — Comunidad extendida (4 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 43 | `fact_achievements` | `achievement_id` | `fact_achievements` | 🔲 Nueva | Logros definidos por juego. Campos: achievement_id, product_id, name, description, icon_url, points, deleted. |
| 44 | `fact_user_achievements` | `user_achievement_id` | `fact_user_achievements` | 🔲 Nueva | Logros desbloqueados. Campos: user_achievement_id, user_id, achievement_id, unlocked_at, deleted. |
| 45 | `fact_forum_threads` | `thread_id` | `fact_forum_threads` | 🔲 Nueva | Hilos de foro por juego. Campos: thread_id, product_id, author_id, title, pinned, created_at, deleted. |
| 46 | `fact_forum_posts` | `post_id` | `fact_forum_posts` | 🔲 Nueva | Posts en hilos. Campos: post_id, thread_id, author_id, body, created_at, edited_at, deleted. |

---

### J. REALTIME — Family sharing (2 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 47 | `fact_family_groups` | `group_id` | `fact_family_groups` | 🔲 Nueva | Grupo familiar. Campos: group_id, owner_id, name, max_members, created_at, deleted. |
| 48 | `fact_family_shares` | `share_id` | `fact_family_shares` | 🔲 Nueva | Biblioteca compartida. Campos: share_id, group_id, purchase_id, shared_by, shared_with, created_at, deleted. |

---

### K. REALTIME — API B2B y analytics (2 tablas)

| # | Tabla | PK | Topic Kafka | Estado | Descripción |
|---|-------|-----|-------------|--------|-------------|
| 49 | `fact_api_keys` | `key_id` | `fact_api_keys` | 🔲 Nueva | Claves API partners. Campos: key_id, partner_id, key_hash, scopes, rate_limit, expires_at, deleted. |
| 50 | `fact_search_queries` | `query_id` | `fact_search_queries` | 🔲 Nueva | Log de búsquedas (analytics). Campos: query_id, user_id, query_text, results_count, created_at. |

---

## 7. Topics Kafka (40 topics REALTIME)

Cada tabla REALTIME tiene un topic homónimo. Clave de partición = PK de la tabla.

```
fact_users, fact_user_sessions, fact_user_wallets, fact_wallet_transactions,
fact_cart, fact_orders, fact_order_items, fact_payments, fact_purchases,
fact_refunds, fact_gifts, fact_coupons, fact_coupon_redemptions, fact_promotions,
fact_wishlist, fact_wishlist_price_alerts, fact_reviews, fact_review_votes,
fact_user_events, fact_friendships, fact_user_activity, fact_notifications,
fact_builds, fact_download_tokens, fact_install_states, fact_play_sessions,
emp_records, fact_partner_accounts, fact_partner_games, fact_revenue_snapshots,
fact_support_tickets, fact_user_sanctions, fact_achievements, fact_user_achievements,
fact_forum_threads, fact_forum_posts, fact_family_groups, fact_family_shares,
fact_api_keys, fact_search_queries
```

---

## 8. Flujos críticos

### Compra (checkout)
```
fact_cart → fact_orders + fact_order_items → fact_payments
→ fact_purchases (biblioteca) → tombstone fact_cart
→ fact_user_events (purchase_completed)
```

### Reseña verificada
```
GET fact_purchases (user_id + product_id) → fact_reviews (kafka_send)
```

### Descarga
```
GET fact_purchases (owned) → fact_download_tokens (token 15 min)
→ GET fact_builds (file_path) → object storage
```

### Biblioteca
```
GET fact_purchases WHERE user_id = ? AND deleted = FALSE
(sin tabla library separada)
```

---

## 9. Reglas globales (heredadas P1–P6)

| Código | Regla |
|--------|-------|
| P1 | Toda escritura REALTIME pasa por `kafka_send(topic, pk, payload)`. |
| P2 | Borrado lógico con `deleted=TRUE` (tombstone). |
| P3 | Sin PocketBase ni otras bases de datos. |
| P4 | Consistencia eventual < 2 s entre Kafka y Pinot. |
| P5 | Secretos solo en backend (.env / docker env). |
| P6 | Catálogo OFFLINE filtrado por `semana <= N`. |
| P7 | Pagos y wallet DEBEN usar `idempotency_key` para evitar doble cargo. |
| P8 | Toda query con input de usuario pasa por `_esc()`. |

---

## 10. Módulos backend (FastAPI) por dominio

| Módulo | Prefijo API | Tablas que consume/escribe |
|--------|-------------|----------------------------|
| `auth` | `/auth` | fact_users, fact_user_sessions |
| `wallet` | `/wallet` | fact_user_wallets, fact_wallet_transactions |
| `store` | `/store` | fact_videogames, fact_game_products, fact_price_catalog, fact_promotions |
| `cart` | `/cart` | fact_cart, fact_coupons |
| `checkout` | `/checkout` | fact_orders, fact_order_items, fact_payments, fact_purchases |
| `library` | `/library` | fact_purchases (solo lectura) |
| `refunds` | `/refunds` | fact_refunds |
| `gifts` | `/gifts` | fact_gifts |
| `user` | `/user` | fact_wishlist, fact_wishlist_price_alerts |
| `reviews` | `/reviews` | fact_reviews, fact_review_votes |
| `social` | `/social` | fact_friendships, fact_user_activity |
| `notifications` | `/notifications` | fact_notifications |
| `downloads` | `/downloads` | fact_builds, fact_download_tokens, fact_install_states |
| `play` | `/play` | fact_play_sessions, fact_user_achievements |
| `achievements` | `/achievements` | fact_achievements |
| `forums` | `/forums` | fact_forum_threads, fact_forum_posts |
| `family` | `/family` | fact_family_groups, fact_family_shares |
| `partner` | `/partner` | fact_partner_accounts, fact_partner_games, fact_api_keys |
| `empresa` | `/empresa` | emp_records |
| `support` | `/support` | fact_support_tickets |
| `dashboard` | `/api/dashboard` | fact_videogames, dim_*, fact_user_events, fact_search_queries |
| `games` | `/api/games` | fact_videogames (legacy) |
| `dimensiones` | `/dimensiones` | dim_* |

---

## 11. Fases de implementación

| Fase | Tablas nuevas | Acumulado | Hito |
|------|---------------|-----------|------|
| **0 — Actual** | 0 | 9 | Demo analítica + wishlist |
| **1 — Comercio** | +13 | 22 | Comprar, biblioteca, reseñar |
| **2 — Tienda pro** | +8 | 30 | Promos, wallet, regalos, eventos |
| **3 — Distribución** | +6 | 36 | Launcher, descargas, tiempo jugado |
| **4 — Ecosistema** | +8 | 44 | Social, publisher, soporte |
| **5 — Steam completo** | +6 | **50** | Logros, foros, family, API B2B |

### Detalle por fase

**Fase 1 (+13):** fact_game_products, fact_price_catalog, fact_cart, fact_orders, fact_order_items, fact_payments, fact_purchases, fact_refunds, fact_reviews, fact_bundles, fact_bundle_items, fact_user_sessions, fact_promotions

**Fase 2 (+8):** fact_user_wallets, fact_wallet_transactions, fact_gifts, fact_coupons, fact_coupon_redemptions, fact_wishlist_price_alerts, fact_review_votes, fact_user_events

**Fase 3 (+6):** fact_builds, fact_download_tokens, fact_install_states, fact_play_sessions, fact_achievements, fact_user_achievements

**Fase 4 (+8):** fact_friendships, fact_user_activity, fact_notifications, fact_partner_accounts, fact_partner_games, fact_revenue_snapshots, fact_support_tickets, fact_user_sanctions

**Fase 5 (+6):** fact_forum_threads, fact_forum_posts, fact_family_groups, fact_family_shares, fact_api_keys, fact_search_queries

---

## 12. Fuera de alcance

- Otra base de datos distinta de Pinot.
- Kubernetes / Helm en fase actual.
- DRM de grado comercial (Denuvo, etc.).
- CDN global multi-región (solo MinIO local en Docker).
- Modelos ML en producción.
