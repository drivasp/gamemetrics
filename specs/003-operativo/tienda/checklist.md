# Checklist de Validación — tienda [Implementado]

## Seguridad (C3, Q2)
- [ ] `_esc()` / escape aplicado a `genre`, `platform` y `search` antes de insertarlos en queries Pinot
- [ ] La clave de API de RAWG solo existe en el backend (variable de entorno); nunca llega al frontend
- [ ] Ningún endpoint de tienda requiere JWT (acceso público)

## Flujo de datos (P6)
- [ ] Todos los endpoints usan `WHERE semana <= N` (no `semana = N`)
- [ ] Parámetro `semana` tiene valor por defecto 17 en todos los endpoints
- [ ] Ningún endpoint de tienda escribe datos (solo lectura de Pinot OFFLINE)

## Orden del router (C2)
- [ ] `/store/games/{slug}` está registrado ÚLTIMO en `store/router.py` (no captura rutas anteriores)
- [ ] Rutas específicas (`/featured`, `/new-releases`, `/popular`, `/free-games`, `/games`) están antes del `/{slug}`

## Funcionalidad
- [ ] GET /store/featured retorna ≤ 6 juegos con metacritic > 80 y rating > 4
- [ ] GET /store/new-releases retorna ≤ 12 juegos ordenados por fecha DESC
- [ ] GET /store/popular retorna ≤ 20 juegos con rating > 0
- [ ] GET /store/free-games retorna juegos con is_free=true
- [ ] GET /store/games retorna StorePageDTO con `total` correcto
- [ ] GET /store/games con filtros combina condiciones con AND
- [ ] GET /store/games/{slug} de slug válido retorna StoreGameDetailDTO
- [ ] GET /store/games/{slug} de slug inválido retorna HTTP 404
- [ ] Todos los juegos tienen `price` (float) e `is_free` (bool) en la respuesta

## Degradación elegante (P4)
- [ ] Si RAWG API no responde, se usa `placeholder_image(name)` en lugar de crashear
- [ ] El campo `background_image` puede ser null sin romper el frontend

## Rendimiento (RNF-STORE-001)
- [ ] GET /store/games (24 resultados con RAWG) responde en < 3 s
- [ ] asyncio.gather usado en `listar_juegos.py` (query + count en paralelo)
- [ ] asyncio.gather usado en `detalle_juego.py` (RAWG + similares en paralelo)

## DTOs (C5)
- [ ] Todos los endpoints tienen `response_model` explícito
- [ ] `StoreGameDetailDTO` hereda de `StoreGameDTO` correctamente
