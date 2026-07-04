# Tareas — biblioteca [Planificado]

## Backend
- [ ] T-LIB-01: Crear `library/modelos_library.py` con LibraryItemDTO
- [ ] T-LIB-02: Implementar `library/listar.py` — GET /library (purchases WHERE user_id, ORDER BY purchased_at DESC LIMIT 500)
- [ ] T-LIB-03: Implementar `library/verificar.py` — GET /library/check/{game_slug} (retorna {owned: bool})
- [ ] T-LIB-04: Crear `library/router.py` con prefix="/library" y los 2 endpoints (verificar primero)
- [ ] T-LIB-05: Registrar `library_router` en `backend/main.py`
- [ ] T-LIB-06: Asegurar que `_esc()` se aplica a user_id y game_slug en queries

## Frontend
- [ ] T-LIB-07: Crear `LibraryComponent` en Angular con cuadrícula de juegos comprados
- [ ] T-LIB-08: Implementar `LibraryService` con métodos `getLibrary()` y `checkOwned(slug)`
- [ ] T-LIB-09: Agregar ruta `/library` en `app.routes.ts` con `canActivate: [authGuard]`
- [ ] T-LIB-10: Mostrar botón "Ir a mi biblioteca" en `StoreGameDetailComponent` si el usuario ya posee el juego

## Integración
- [ ] T-LIB-11: Verificar que el endpoint `GET /library/check/{slug}` es consumible desde el paquete carrito (validación anti-duplicado de compra)
- [ ] T-LIB-12: Verificar que el endpoint es consumible desde el paquete reseñas (validación de compra verificada)
