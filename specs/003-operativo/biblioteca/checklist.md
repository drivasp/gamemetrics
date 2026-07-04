# Checklist de Validación — biblioteca [Planificado]

## Solo lectura (regla de arquitectura)
- [ ] El módulo biblioteca NO tiene ningún endpoint POST, PUT, PATCH ni DELETE
- [ ] Ningún endpoint escribe directamente en `purchases`; la escritura la hace el paquete carrito vía Kafka

## Seguridad (Q2, C3)
- [ ] Todos los endpoints validan JWT Bearer
- [ ] `_esc()` aplicado a `user_id` y `game_slug` en queries Pinot
- [ ] El user_id viene del JWT, nunca del path ni del body

## Orden del router (C2)
- [ ] `GET /library/check/{game_slug}` está registrado ANTES de cualquier otra ruta con parámetro de path

## Funcionalidad
- [ ] GET /library retorna LibraryItemDTO con campos: purchase_id, game_slug, game_name, amount, purchased_at
- [ ] GET /library sin token retorna HTTP 401
- [ ] GET /library/check/{slug} retorna {owned: true} para juego comprado
- [ ] GET /library/check/{slug} retorna {owned: false} para juego no comprado
- [ ] GET /library retorna [] para usuario sin compras (no error)

## Consistencia eventual (P4)
- [ ] Un juego aparece en GET /library en < 2 s tras su evento Kafka de compra (paquete carrito)

## Integración
- [ ] El paquete carrito usa GET /library/check/{slug} para bloquear compras duplicadas
- [ ] El paquete reseñas usa GET /library/check/{slug} para validar reseña verificada

## Módulo (C1)
- [ ] `library_router` registrado en `backend/main.py`
- [ ] Archivos separados por responsabilidad (listar.py, verificar.py)
