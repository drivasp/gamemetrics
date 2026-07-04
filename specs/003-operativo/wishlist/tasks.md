# Tareas — wishlist [Implementado]

- [x] T-WISH-01: Implementar `user/modelos_user.py` con WishlistItemDTO y AddWishlistDTO
- [x] T-WISH-02: Implementar `user/wishlist.py` con helper `_require_token()` y función `_esc()`
- [x] T-WISH-03: Implementar `GET /user/wishlist/check/{game_slug}` (registrado PRIMERO en el módulo)
- [x] T-WISH-04: Implementar `GET /user/wishlist` con filtro por user_id y ORDER BY created_at DESC LIMIT 500
- [x] T-WISH-05: Implementar `POST /user/wishlist` con verificación de duplicado (HTTP 409) y kafka_send
- [x] T-WISH-06: Implementar `DELETE /user/wishlist/{game_slug}` con verificación de existencia y tombstone Kafka
- [x] T-WISH-07: Implementar `user/router.py` con wishlist_router bajo prefijo "/user"
- [x] T-WISH-08: Registrar `user_router` en `backend/main.py`
- [x] T-WISH-09: Implementar `WishlistComponent` en Angular con lista y botón de eliminar
- [x] T-WISH-10: Implementar botón "Agregar a Wishlist" en `StoreGameDetailComponent`
- [x] T-WISH-11: Implementar `WishlistService` en Angular con los 4 métodos
- [ ] T-WISH-12: Agregar indicador visual en detalle del juego cuando el juego ya está en wishlist (check previo a la carga)
- [ ] T-WISH-13: Agregar funcionalidad "Mover al carrito" desde la wishlist (requiere paquete carrito [Planificado])
- [ ] T-WISH-14: Implementar límite máximo de 200 items por wishlist con HTTP 400 al excederse
