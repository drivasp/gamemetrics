# Paquete tienda — Tienda de Videojuegos [Implementado]

## 1. Nombre del paquete
**tienda** (store) — Home, Catálogo con Filtros y Detalle de Juego

## 2. Objetivo
Proveer al Visitante y al Usuario Registrado una experiencia de navegación y descubrimiento del catálogo de videojuegos: página de inicio con secciones destacadas, catálogo paginado con filtros combinables y página de detalle con información enriquecida desde RAWG API y juegos similares.

## 3. Contexto
El catálogo de ~1.7 millones de títulos vive en Pinot OFFLINE (`fact_videogames`). Las secciones del home (featured, new-releases, popular, free-games) son subsets predefinidos ordenados por criterios distintos. El catálogo completo acepta filtros por género, plataforma, búsqueda de texto, precio y semana, con paginación. El detalle de juego enriquece los datos locales con imágenes y descripción de la RAWG API (externa). El precio se calcula dinámicamente con la fórmula global del sistema.

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Tienda
- **Paquete:** tienda (store)

## 5. Actores

| Actor | Rol |
|-------|-----|
| Visitante | Puede navegar el home, catálogo y detalle sin autenticación. |
| Usuario Registrado | Igual que Visitante; además puede agregar juegos a la wishlist desde el detalle. |
| Sistema (RAWG API) | Proveedor externo de imágenes de fondo, screenshots y descripciones. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O06 | Ver home de la tienda (secciones destacadas) | Visitante, Usuario Registrado | OE2 |
| CU-O07 | Navegar catálogo con filtros y paginación | Visitante, Usuario Registrado | OE2 |
| CU-O08 | Ver detalle de un juego | Visitante, Usuario Registrado | OE2 |
| CU-O09 | Filtrar catálogo por género | Visitante, Usuario Registrado | OE2 |
| CU-O10 | Filtrar catálogo por plataforma | Visitante, Usuario Registrado | OE2 |
| CU-O11 | Buscar juego por nombre | Visitante, Usuario Registrado | OE2 |
| CU-O12 | Filtrar por precio (gratis / de pago) | Visitante, Usuario Registrado | OE2 |
| CU-O13 | Ordenar catálogo por criterio | Visitante, Usuario Registrado | OE2 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-STORE-001 | Como Visitante, quiero ver los juegos destacados en el home para descubrir títulos de alta calidad. |
| US-STORE-002 | Como Visitante, quiero ver los nuevos lanzamientos para conocer los juegos más recientes del catálogo. |
| US-STORE-003 | Como Visitante, quiero ver los juegos más populares por rating para encontrar los favoritos de la comunidad. |
| US-STORE-004 | Como Visitante, quiero ver juegos gratuitos para explorar el catálogo sin costo. |
| US-STORE-005 | Como Visitante, quiero buscar juegos por nombre para encontrar un título específico rápidamente. |
| US-STORE-006 | Como Visitante, quiero filtrar el catálogo por género y plataforma para acotar los resultados a mis preferencias. |
| US-STORE-007 | Como Visitante, quiero ver el precio de cada juego para decidir si me interesa comprarlo. |
| US-STORE-008 | Como Visitante, quiero ver el detalle completo de un juego (imagen, descripción, screenshots, juegos similares) para tomar una decisión informada. |
| US-STORE-009 | Como Visitante, quiero paginar el catálogo para explorar más de 24 juegos sin sobrecargar la pantalla. |
| US-STORE-010 | Como Visitante, quiero ordenar el catálogo por rating, metacritic, fecha o precio para organizar los resultados según mi criterio. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-STORE-001 | El sistema MUST proveer `GET /store/featured?semana=N` que retorne hasta 6 juegos con `metacritic > 80` y `rating > 4`, ordenados por `metacritic DESC`. |
| RF-STORE-002 | El sistema MUST proveer `GET /store/new-releases?semana=N` que retorne hasta 12 juegos con `released_ts > 0`, ordenados por `released_ts DESC`. |
| RF-STORE-003 | El sistema MUST proveer `GET /store/popular?semana=N` que retorne hasta 20 juegos con `rating > 0`, ordenados por `rating DESC`. |
| RF-STORE-004 | El sistema MUST proveer `GET /store/free-games?semana=N` que retorne hasta 12 juegos con `rating = 0 AND metacritic = 0`. |
| RF-STORE-005 | El sistema MUST proveer `GET /store/games` con los parámetros: `page` (int, 0+), `size` (int), `semana` (int, defecto 17), `genre` (str), `platform` (str), `search` (str), `order_by` (str), `price_filter` (str: `free`/`paid`/vacío). |
| RF-STORE-006 | El endpoint `/store/games` MUST retornar `StorePageDTO`: `{games, total, page, size}` con paginación basada en `LIMIT size OFFSET page*size`. |
| RF-STORE-007 | El endpoint `/store/games` MUST soportar los siguientes criterios de ordenamiento: `rating` (defecto), `metacritic`, `released`, `name`, `price_asc`, `price_desc`. |
| RF-STORE-008 | El sistema MUST proveer `GET /store/games/{slug}` que retorne `StoreGameDetailDTO` con descripción, screenshots y hasta 4 juegos similares del mismo género. |
| RF-STORE-009 | El endpoint `/store/games/{slug}` MUST estar registrado ÚLTIMO en el router para no capturar rutas específicas previas (convención C2). |
| RF-STORE-010 | Todos los endpoints de tienda MUST enriquecer los juegos con imagen de fondo desde RAWG API; si RAWG falla, MUST usar imagen placeholder generada localmente. |
| RF-STORE-011 | Todos los endpoints de tienda MUST aplicar la fórmula de precio `calc_price(rating, metacritic)` a cada juego y exponer los campos `price` e `is_free`. |
| RF-STORE-012 | El sistema MUST escapar todos los parámetros de texto (`genre`, `platform`, `search`) antes de insertarlos en queries Pinot (convención C3). |
| RF-STORE-013 | Los filtros de catálogo MUST combinarse como condiciones AND: `semana <= N AND genres LIKE '%genre%' AND platforms LIKE '%platform%' AND name LIKE '%search%'`. |
| RF-STORE-014 | El endpoint `/store/games` MUST ejecutar la consulta de datos y el COUNT en paralelo (asyncio.gather) para minimizar latencia. |
| RF-STORE-015 | Los endpoints de tienda MUST ser accesibles sin autenticación (Visitante). |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-STORE-001 | El catálogo paginado (24 resultados) MUST responder en menos de 3 segundos incluyendo enriquecimiento RAWG. |
| RNF-STORE-002 | El detalle de juego MUST responder en menos de 3 segundos (Pinot + RAWG + similares en paralelo). |
| RNF-STORE-003 | Las secciones del home (featured, popular, etc.) SHOULD responder en menos de 2 segundos. |
| RNF-STORE-004 | Si RAWG API no responde, el sistema MUST continuar usando imágenes placeholder (degradación elegante). |
| RNF-STORE-005 | El catálogo MUST ser accesible sin autenticación; no se requiere JWT. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-STORE-001 | El filtro por semana siempre usa `semana <= N` (acumulado), no `semana = N`. |
| RN-STORE-002 | La fórmula de precio es global y fija: `price = max(1.99, rating*8 + metacritic*0.4)`. Si ambos son 0 → `price = 0.00` (gratis). |
| RN-STORE-003 | Los juegos destacados son aquellos con `metacritic > 80` y `rating > 4`; este umbral no es configurable. |
| RN-STORE-004 | Los juegos similares en el detalle son los 4 mejor valorados del mismo primer género, excluyendo el juego actual. |
| RN-STORE-005 | La búsqueda de texto en catálogo usa `LIKE '%search%'` sobre el campo `name`; no es búsqueda de texto completo. |
| RN-STORE-006 | El tamaño de página por defecto del catálogo es 24 juegos; el máximo depende del parámetro `size` enviado. |
| RN-STORE-007 | La clave de API de RAWG vive solo en el backend (variable de entorno). El frontend nunca la recibe. |

## 11. Entradas y salidas

| Endpoint | Entrada (query params) | Salida |
|----------|----------------------|--------|
| `GET /store/featured` | `semana=17` | `list[StoreGameDTO]` (máx. 6) |
| `GET /store/new-releases` | `semana=17` | `list[StoreGameDTO]` (máx. 12) |
| `GET /store/popular` | `semana=17` | `list[StoreGameDTO]` (máx. 20) |
| `GET /store/free-games` | `semana=17` | `list[StoreGameDTO]` (máx. 12) |
| `GET /store/games` | `page, size, semana, genre, platform, search, order_by, price_filter` | `StorePageDTO {games, total, page, size}` |
| `GET /store/games/{slug}` | `slug` (path) | `StoreGameDetailDTO` |

**StoreGameDTO:** `{id, slug, name, released, rating, metacritic, genres, platforms, developers, publishers, esrb_rating, price, is_free, background_image?}`

**StoreGameDetailDTO:** `StoreGameDTO` + `{description?, screenshots: [], similar: [StoreGameDTO]}`

## 12. Escenarios Gherkin

**Escenario: Ver juegos destacados (CU-O06)**
```gherkin
Dado que el Visitante accede al home de la tienda
Cuando el frontend llama a GET /store/featured?semana=17
Entonces el backend consulta Pinot con WHERE semana <= 17 AND metacritic > 80 AND rating > 4 ORDER BY metacritic DESC LIMIT 6
Y enriquece con imágenes RAWG
Y retorna hasta 6 StoreGameDTO con precio calculado en menos de 2 segundos
```

**Escenario: Catálogo con filtros combinados (CU-O07)**
```gherkin
Dado que el Visitante filtra por genre="Action" y platform="PC" y search="zelda"
Cuando llama a GET /store/games?genre=Action&platform=PC&search=zelda&semana=17&page=0&size=24
Entonces el backend construye WHERE semana <= 17 AND genres LIKE '%Action%' AND platforms LIKE '%PC%' AND name LIKE '%zelda%'
Y retorna StorePageDTO con los juegos coincidentes y total
```

**Escenario: Catálogo sin filtros (CU-O07)**
```gherkin
Dado que el Visitante no aplica ningún filtro
Cuando llama a GET /store/games?semana=17&page=0&size=24&order_by=rating
Entonces el backend retorna los 24 juegos mejor valorados del catálogo completo
Y el campo total refleja el total de juegos en semana <= 17
```

**Escenario: Detalle de juego existente (CU-O08)**
```gherkin
Dado que existe un juego con slug "the-witcher-3-wild-hunt" en fact_videogames
Cuando el Visitante llama a GET /store/games/the-witcher-3-wild-hunt
Entonces el backend consulta Pinot por slug
Y en paralelo consulta RAWG API y busca 4 similares del mismo género
Y retorna StoreGameDetailDTO con imagen, descripción, screenshots y similares
```

**Escenario: Detalle de juego inexistente**
```gherkin
Dado que el slug "juego-inventado" no existe en fact_videogames
Cuando llama a GET /store/games/juego-inventado
Entonces retorna HTTP 404 con detalle "Game not found"
```

**Escenario: RAWG API no responde**
```gherkin
Dado que la RAWG API está caída o tarda demasiado
Cuando el backend llama a get_media(slug)
Entonces usa placeholder_image(name) como imagen de fondo
Y retorna el StoreGameDTO igualmente (degradación elegante)
```

**Escenario: Filtro de juegos gratuitos**
```gherkin
Dado que el Visitante aplica price_filter="free"
Cuando llama a GET /store/games?price_filter=free
Entonces el backend agrega la condición AND (rating = 0 AND metacritic = 0)
Y retorna solo juegos con price = 0.00
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-STORE-001 | GET /store/featured retorna entre 1 y 6 juegos con metacritic > 80 y rating > 4. |
| CA-STORE-002 | GET /store/new-releases retorna juegos ordenados por fecha de lanzamiento descendente. |
| CA-STORE-003 | GET /store/popular retorna juegos con rating > 0, ordenados por rating DESC. |
| CA-STORE-004 | GET /store/free-games retorna juegos con is_free=true y price=0.00. |
| CA-STORE-005 | GET /store/games retorna StorePageDTO con campo `total` reflejando el conteo total (no solo la página). |
| CA-STORE-006 | GET /store/games?genre=Action retorna solo juegos cuyo campo `genres` contiene "Action". |
| CA-STORE-007 | GET /store/games?search=mario retorna solo juegos cuyo nombre contiene "mario" (case-insensitive en Pinot). |
| CA-STORE-008 | GET /store/games/{slug} de un slug válido retorna HTTP 200 con campo `description` y array `screenshots`. |
| CA-STORE-009 | GET /store/games/{slug} de un slug inválido retorna HTTP 404. |
| CA-STORE-010 | Todos los juegos retornados tienen campo `price` (float) e `is_free` (bool) calculados correctamente. |
| CA-STORE-011 | Todos los endpoints de tienda responden sin token JWT (no requieren autenticación). |

## 14. Dependencias

| Paquete / Recurso | Tipo |
|-------------------|------|
| `fact_videogames` (Pinot OFFLINE) | Fuente de datos del catálogo. |
| `shared/cliente_pinot.py` | Consultas Pinot (TABLE, GAME_COLUMNS, pinot_query). |
| `shared/helpers_filas.py` | `map_game()` para mapear filas Pinot a DTOs. |
| `store/calcular_precio.py` | `calc_price()`, `enrich()`, `placeholder_image()`. |
| `store/cliente_rawg.py` | `get_media(slug)` para imágenes y descripción. |
| `store/modelos_store.py` | DTOs Pydantic: StoreGameDTO, StorePageDTO, StoreGameDetailDTO. |
| `paquete wishlist` | El botón "Agregar a wishlist" en el detalle depende del paquete wishlist (requiere auth). |

## 15. Fuera de alcance

- Sistema de compra (paquete carrito — planificado).
- Reseñas de usuarios en el detalle (paquete resenas — planificado).
- Búsqueda de texto completo (full-text search) — Pinot usa LIKE.
- Caché de respuestas de RAWG API (mejora de rendimiento pendiente).
- Filtros por rango de precio (precio mínimo/máximo).
- Internacionalización de precios (actualmente en USD implícito).
