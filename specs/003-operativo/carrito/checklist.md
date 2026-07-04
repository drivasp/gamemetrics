# Checklist de Validación — carrito [Planificado]

## Infraestructura (P1, P2, P3)
- [ ] Schemas Pinot de `fact_cart` y `purchases` creados en `etl/pinot_schemas/`
- [ ] Topics Kafka `fact_cart` y `purchases` existen en el broker
- [ ] Tablas Pinot REALTIME `fact_cart` y `purchases` creadas con upsert y deleteRecordColumn
- [ ] Sin referencias a PocketBase ni escrituras directas a Pinot

## Seguridad (P5, Q1, Q2)
- [ ] Claves Stripe sandbox solo en variables de entorno del backend
- [ ] Todos los endpoints validan JWT Bearer (HTTP 401 sin token)
- [ ] El user_id viene del JWT, nunca del body del request

## Flujo Kafka (P1, C4)
- [ ] POST /cart/items → kafka_send("fact_cart", cart_item_id, {...})
- [ ] DELETE /cart/items/{slug} → tombstone en fact_cart (deleted=True)
- [ ] POST /cart/checkout → kafka_send("purchases", purchase_id, {...}) por cada item
- [ ] POST /cart/checkout → tombstone en fact_cart para todos los items del carrito

## Reglas de negocio
- [ ] Agregar juego ya en biblioteca retorna HTTP 409
- [ ] Agregar juego duplicado en carrito retorna HTTP 409
- [ ] Checkout vacía el carrito automáticamente tras éxito

## Módulo backend (C1)
- [ ] `cart/router.py` con prefix="/cart" y todos los endpoints
- [ ] `cart_router` registrado en `backend/main.py`
- [ ] Archivos separados por responsabilidad (agregar, listar, eliminar, vaciar, checkout)

## Frontend (C6)
- [ ] Rutas `/cart` y `/checkout` en `app.routes.ts` con `canActivate: [authGuard]`
- [ ] `CartService` implementado con todos los métodos
- [ ] Botón "Agregar al carrito" en `StoreGameDetailComponent`
