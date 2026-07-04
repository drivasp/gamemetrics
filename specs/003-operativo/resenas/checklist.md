# Checklist de Validación — resenas [Planificado]

## Infraestructura (P1, P2, P3)
- [ ] Schema Pinot `reviews` creado en `etl/pinot_schemas/reviews_schema.json`
- [ ] Topic Kafka `reviews` existe en el broker
- [ ] Tabla Pinot REALTIME `reviews` creada con upsert (`review_id` como PK) y `deleteRecordColumn`
- [ ] Sin referencias a PocketBase ni escrituras directas a Pinot

## Seguridad (Q2, C3)
- [ ] POST, PUT, DELETE validan JWT Bearer (HTTP 401 sin token)
- [ ] GET /reviews/{slug} es público (sin JWT)
- [ ] PUT y DELETE verifican que `user_id` del JWT coincide con el `user_id` de la reseña (HTTP 403 si no es autor)
- [ ] `_esc()` aplicado a `user_id` y `game_slug` en todas las queries Pinot

## Verificación de compra (RN-REV-001)
- [ ] POST consulta `purchases` antes de crear la reseña
- [ ] Si no hay compra verificada → HTTP 403 "Debes comprar el juego para poder reseñarlo"
- [ ] La verificación no depende del paquete carrito directamente (consulta `purchases` en Pinot)

## Flujo Kafka (P1, C4, P2)
- [ ] POST → kafka_send("reviews", review_id, {..., deleted: false})
- [ ] PUT → kafka_send("reviews", review_id, {...}) con datos actualizados (upsert)
- [ ] DELETE → tombstone kafka_send("reviews", review_id, {..., deleted: true})
- [ ] Ningún endpoint escribe directamente a Pinot

## Reglas de negocio
- [ ] Una reseña duplicada (mismo user+slug) retorna HTTP 409
- [ ] Rating fuera de [1-5] retorna HTTP 422 (validación Pydantic)
- [ ] Solo el autor puede editar o eliminar su reseña

## Funcionalidad
- [ ] POST /reviews/{slug} de comprador retorna HTTP 201
- [ ] POST /reviews/{slug} de no-comprador retorna HTTP 403
- [ ] GET /reviews/{slug} retorna ReviewPageDTO con avg_rating y total (sin JWT)
- [ ] PUT /reviews/{slug} actualiza rating y/o comment del autor
- [ ] DELETE /reviews/{slug} retorna HTTP 204 y tombstone

## Consistencia eventual (P4)
- [ ] Reseña visible en GET /reviews/{slug} en < 2 s tras su creación

## Módulo (C1)
- [ ] `reviews_router` registrado en `backend/main.py`
- [ ] Archivos separados por responsabilidad (crear, listar, editar, eliminar)
