# Plan Técnico — 50 tablas Pinot (GameMetrics Cloud)

## Diagrama de arquitectura

```
                    ┌─────────────────────────────────────┐
                    │         Angular 21 SPA              │
                    │  Store · Library · Launcher · Social│
                    └──────────────────┬──────────────────┘
                                       │ HTTP
                    ┌──────────────────▼──────────────────┐
                    │           FastAPI (módulos)          │
                    │  22 routers por dominio              │
                    └───────┬──────────────────┬──────────┘
                            │ kafka_send       │ pinot_query
              ┌─────────────▼──────┐    ┌──────▼──────────────┐
              │   Kafka (40 topics) │    │   Apache Pinot      │
              │   upsert por PK     │───▶│  OFFLINE: 10 tablas │
              └────────────────────┘    │  REALTIME: 40 tablas│
                                        └─────────────────────┘
                            ┌───────────┴───────────┐
                            │  MinIO (binarios)     │
                            │  builds, avatars      │
                            └───────────────────────┘
```

## Convención de archivos ETL por tabla

Cada tabla REALTIME nueva requiere en `etl/pinot_schemas/`:

```
schema_{tabla}.json    — dimensiones, PK, dateTime
table_{tabla}.json     — REALTIME config, streamConfigs, upsertConfig
```

Script `08_create_realtime_tables.py` se extiende para crear las 40 tablas REALTIME.

Cada tabla OFFLINE nueva requiere script ETL dedicado o extensión de `07_create_dimensions.py` / `04_ingest_pinot.py`.

## Patrón kafka_send (todas las tablas REALTIME)

```python
await kafka_send("fact_purchases", purchase_id, {
    "purchase_id": purchase_id,
    "user_id": user_id,
    "product_id": product_id,
    "game_slug": slug,
    "amount": 29.99,
    "purchased_at": int(time.time() * 1000),
    "deleted": False,
})
```

Tombstone:

```python
await kafka_send("fact_cart", cart_item_id, {
    "cart_item_id": cart_item_id,
    "user_id": user_id,
    "deleted": True,
    ...
})
```

## Relaciones lógicas (sin FK en Pinot)

```
fact_users ──┬── fact_cart ──► fact_orders ──► fact_payments
             │                      │
             │                      └── fact_order_items
             │                      └── fact_purchases (biblioteca)
             │                              │
             ├── fact_wishlist              ├── fact_reviews (requiere purchase)
             ├── fact_reviews               ├── fact_gifts
             ├── fact_play_sessions         ├── fact_install_states
             └── fact_user_wallets          └── fact_download_tokens

fact_videogames (OFFLINE) ──► fact_game_products (OFFLINE)
                            ──► fact_price_catalog (OFFLINE)
                            ──► fact_bundles + fact_bundle_items

fact_partner_accounts ──► fact_partner_games ──► fact_game_products
                       ──► fact_api_keys
                       ──► fact_revenue_snapshots
```

## Precio final (regla de negocio)

```
1. base = fact_price_catalog[product_id, region, currency]
2. si no existe → fallback fórmula: max(1.99, rating*8 + metacritic*0.4)
3. aplicar fact_promotions activas (REALTIME)
4. aplicar fact_coupons si redemption válida (REALTIME)
5. precio final nunca < 0
```

## Checklist por tabla nueva

- [ ] `schema_{name}.json` en `etl/pinot_schemas/`
- [ ] `table_{name}.json` (solo REALTIME)
- [ ] Topic Kafka creado
- [ ] Entrada en `08_create_realtime_tables.py` o script OFFLINE
- [ ] Módulo FastAPI con router
- [ ] DTOs Pydantic
- [ ] Servicio Angular (si tiene UI)
- [ ] Entrada en spec 004
