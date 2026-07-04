# Tareas — tienda [Implementado]

- [x] T-STORE-01: Implementar `store/modelos_store.py` con StoreGameDTO, StorePageDTO, StoreGameDetailDTO, GameMediaDTO
- [x] T-STORE-02: Implementar `store/calcular_precio.py` con `calc_price()`, `enrich()`, `placeholder_image()`, `to_store()`
- [x] T-STORE-03: Implementar `store/cliente_rawg.py` con `get_media(slug)` que retorna imagen, descripción y screenshots
- [x] T-STORE-04: Implementar `store/juegos_destacados.py` — GET /store/featured (metacritic>80, rating>4, LIMIT 6)
- [x] T-STORE-05: Implementar `store/nuevos_lanzamientos.py` — GET /store/new-releases (released_ts>0, ORDER BY released_ts DESC, LIMIT 12)
- [x] T-STORE-06: Implementar `store/juegos_populares.py` — GET /store/popular (rating>0, ORDER BY rating DESC, LIMIT 20)
- [x] T-STORE-07: Implementar `store/juegos_gratis.py` — GET /store/free-games (rating=0 AND metacritic=0, LIMIT 12)
- [x] T-STORE-08: Implementar `store/listar_juegos.py` — GET /store/games con filtros combinados, paginación, ORDER_MAP y asyncio.gather para count
- [x] T-STORE-09: Implementar `store/detalle_juego.py` — GET /store/games/{slug} con asyncio.gather para RAWG + similares
- [x] T-STORE-10: Implementar `store/router.py` con todos los sub-routers (/{slug} al final)
- [x] T-STORE-11: Registrar `store_router` en `backend/main.py`
- [x] T-STORE-12: Implementar `StoreHomeComponent` en Angular (ruta `/store`) con 4 secciones del home
- [x] T-STORE-13: Implementar `StoreCatalogComponent` en Angular (ruta `/store/catalog`) con filtros y paginación
- [x] T-STORE-14: Implementar `StoreGameDetailComponent` en Angular (ruta `/store/game/:slug`) con detalle y similares
- [x] T-STORE-15: Implementar `StoreService` en Angular con todos los métodos de la tienda
- [ ] T-STORE-16: Agregar caché de respuestas RAWG para reducir latencia en juegos frecuentes
- [ ] T-STORE-17: Implementar filtro por rango de precio (precio_min / precio_max)
- [ ] T-STORE-18: Agregar botón "Comprar" en el detalle (requiere paquete carrito [Planificado])
