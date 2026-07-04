# Checklist de Validación — wishlist [Implementado]

## Seguridad (Q2, C3)
- [ ] Todos los endpoints validan JWT Bearer antes de operar (HTTP 401 si falta o inválido)
- [ ] `_esc()` aplicado a `user_id` y `game_slug` antes de queries Pinot
- [ ] El user_id viene siempre del token JWT, nunca del body del request

## Flujo Kafka (P1, C4, P2)
- [ ] `POST /user/wishlist` llama a `kafka_send("fact_wishlist", wid, {...})`
- [ ] `DELETE /user/wishlist/{slug}` envía tombstone Kafka con `deleted=True` (no DELETE directo a Pinot)
- [ ] Ningún endpoint escribe directamente a Pinot

## Clave de upsert (P2)
- [ ] `wishlist_id` se construye como `f"{user_id}_{game_slug}"` consistentemente
- [ ] La verificación de duplicado usa el mismo `wishlist_id` construido

## Orden del router (C2)
- [ ] `GET /user/wishlist/check/{game_slug}` está registrado ANTES de `DELETE /user/wishlist/{game_slug}`
- [ ] No hay colisión de rutas entre `/wishlist/check/{slug}` y `/wishlist/{slug}`

## Funcionalidad
- [ ] POST /user/wishlist con juego nuevo retorna HTTP 201
- [ ] POST /user/wishlist con duplicado retorna HTTP 409
- [ ] GET /user/wishlist retorna items ordenados por created_at DESC
- [ ] GET /user/wishlist/check/{slug} retorna `{in_wishlist: bool}` correcto
- [ ] DELETE /user/wishlist/{slug} retorna HTTP 204 si existía
- [ ] DELETE /user/wishlist/{slug} retorna HTTP 404 si no existía

## Consistencia eventual (P4)
- [ ] La UI contempla < 2 s de latencia entre POST y visibilidad en GET
- [ ] El tombstone elimina el item del GET posterior (< 2 s)

## DTOs (C5)
- [ ] `POST /user/wishlist` tiene `response_model=WishlistItemDTO, status_code=201`
- [ ] `DELETE /user/wishlist/{slug}` tiene `status_code=204`
