# Tareas — resenas [Planificado]

## ETL / Infraestructura
- [ ] T-REV-01: Crear schema Pinot REALTIME `reviews` en `etl/pinot_schemas/reviews_schema.json`
- [ ] T-REV-02: Crear topic Kafka `reviews` en el script ETL (08 o nuevo script)
- [ ] T-REV-03: Crear tabla Pinot REALTIME `reviews` con upsert por `review_id` y `deleteRecordColumn`

## Backend
- [ ] T-REV-04: Crear `reviews/modelos_reviews.py` con CreateReviewDTO, UpdateReviewDTO, ReviewDTO, ReviewPageDTO
- [ ] T-REV-05: Implementar `reviews/crear.py` — POST /reviews/{game_slug}:
  - Verificar JWT → user_id
  - Verificar compra en `purchases` (HTTP 403 si no compró)
  - Verificar no duplicado en `reviews` (HTTP 409 si ya existe)
  - kafka_send("reviews", review_id, {...})
  - Retornar ReviewDTO HTTP 201
- [ ] T-REV-06: Implementar `reviews/listar.py` — GET /reviews/{game_slug} (público, avg_rating, total)
- [ ] T-REV-07: Implementar `reviews/editar.py` — PUT /reviews/{game_slug} (solo autor, merge parcial, kafka_send)
- [ ] T-REV-08: Implementar `reviews/eliminar.py` — DELETE /reviews/{game_slug} (solo autor, tombstone Kafka)
- [ ] T-REV-09: Crear `reviews/router.py` con todos los endpoints (GET público primero, luego protegidos)
- [ ] T-REV-10: Registrar `reviews_router` en `backend/main.py`

## Frontend
- [ ] T-REV-11: Crear `ReviewsComponent` integrado en `StoreGameDetailComponent` para mostrar reseñas
- [ ] T-REV-12: Crear `WriteReviewComponent` (formulario con selector de estrellas 1-5 y textarea)
- [ ] T-REV-13: Implementar `ReviewsService` con todos los métodos
- [ ] T-REV-14: Mostrar `WriteReviewComponent` solo si el usuario tiene JWT Y posee el juego (`LibraryService.checkOwned()`)
- [ ] T-REV-15: Mostrar rating promedio de reseñas en la tarjeta de la tienda (requiere actualizar StoreGameDTO)
