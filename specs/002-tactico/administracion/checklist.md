# Checklist de Validación — Administración de Plataforma

## Calidad de código
- [ ] `_esc()` aplicado a todos los valores de colección en queries Pinot
- [ ] `VALID_COLLECTIONS` centralizado y sin duplicados
- [ ] Soft delete siempre vía kafka_send con `deleted=True` (nunca DELETE directo a Pinot)
- [ ] Merge en PATCH no pierde campos existentes

## Funcionalidad
- [ ] GET devuelve `{items, totalItems, totalPages, page, perPage}` con paginación correcta
- [ ] POST retorna HTTP 201 con `id` generado por servidor
- [ ] DELETE retorna HTTP 204
- [ ] Colección inválida retorna HTTP 404

## Cumplimiento de principios
- [ ] P1: toda escritura pasa por kafka_send al topic `emp_records`
- [ ] P2: tombstone `deleted=TRUE` en lugar de DELETE físico
- [ ] P3: sin referencias a PocketBase
