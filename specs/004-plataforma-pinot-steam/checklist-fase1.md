# Fase 1 — Checklist de implementación

## Tablas nuevas (13) → Total 22

### OFFLINE
- [x] fact_game_products
- [x] fact_price_catalog
- [x] fact_bundles
- [x] fact_bundle_items

### REALTIME
- [x] fact_cart
- [x] fact_orders
- [x] fact_order_items
- [x] fact_payments
- [x] fact_purchases
- [x] fact_refunds
- [x] fact_reviews
- [x] fact_promotions
- [x] fact_user_sessions

## Backend
- [x] /cart — carrito CRUD
- [x] /checkout — pago sandbox + biblioteca
- [x] /library — biblioteca + check owned
- [x] /reviews — reseñas verificadas
- [x] /refunds — reembolsos 14 días
- [x] Precios desde fact_price_catalog + fact_promotions

## Frontend
- [x] /cart — página carrito estilo Steam
- [x] /library — biblioteca de juegos
- [x] Detalle juego — carrito, owned, reseñas
- [x] Navbar — carrito con badge, biblioteca activa

## ETL (orden de ejecución)
1. Cargar dataset (semana 1+)
2. Crear dimensiones
3. **Crear tablas REALTIME** (paso 4 dashboard)
4. **Cargar catálogo comercial** (paso 5)
5. **Seed promociones** (paso 6)
