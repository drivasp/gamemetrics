# Tareas — carrito [Planificado]

## ETL / Infraestructura
- [ ] T-CART-01: Crear schema Pinot REALTIME `fact_cart` en `etl/pinot_schemas/fact_cart_schema.json`
- [ ] T-CART-02: Crear schema Pinot REALTIME `purchases` en `etl/pinot_schemas/purchases_schema.json`
- [ ] T-CART-03: Crear topics Kafka `fact_cart` y `purchases` en el script ETL 08 o en un nuevo script
- [ ] T-CART-04: Crear tablas Pinot REALTIME `fact_cart` y `purchases` con upsert y deleteRecordColumn

## Backend
- [ ] T-CART-05: Crear `cart/modelos_cart.py` con CartItemDTO, CartDTO, CheckoutResponseDTO
- [ ] T-CART-06: Implementar `cart/agregar.py` — POST /cart/items (verificar no duplicado, no en biblioteca, kafka_send)
- [ ] T-CART-07: Implementar `cart/listar.py` — GET /cart (fact_cart WHERE user_id, calcular total)
- [ ] T-CART-08: Implementar `cart/eliminar.py` — DELETE /cart/items/{slug} (tombstone Kafka)
- [ ] T-CART-09: Implementar `cart/vaciar.py` — DELETE /cart (tombstone a todos los items del usuario)
- [ ] T-CART-10: Implementar `cart/checkout.py` — POST /cart/checkout (Stripe sandbox SDK, emitir purchases vía Kafka, vaciar carrito)
- [ ] T-CART-11: Crear `cart/router.py` con todos los endpoints registrados
- [ ] T-CART-12: Registrar `cart_router` en `backend/main.py`
- [ ] T-CART-13: Agregar `stripe` a `backend/requirements.txt`

## Frontend
- [ ] T-CART-14: Crear `CartComponent` en Angular con lista de items y total
- [ ] T-CART-15: Crear `CheckoutComponent` con formulario Stripe sandbox (Elements o redirect)
- [ ] T-CART-16: Implementar `CartService` con todos los métodos
- [ ] T-CART-17: Agregar rutas `/cart` y `/checkout` en `app.routes.ts` con authGuard
- [ ] T-CART-18: Agregar botón "Agregar al carrito" en `StoreGameDetailComponent`
- [ ] T-CART-19: Agregar indicador de carrito (count de items) en el navbar
