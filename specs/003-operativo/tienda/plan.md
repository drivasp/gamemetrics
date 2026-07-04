# Plan Técnico — tienda [Implementado]

## Tabla Pinot OFFLINE
**fact_videogames** — campos relevantes

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | STRING (PK) | Identificador RAWG |
| `slug` | STRING | URL-friendly, usado en rutas |
| `name` | STRING | Nombre del juego |
| `released` | STRING | Fecha en formato ISO |
| `released_ts` | LONG | Epoch ms (para ordenar por fecha) |
| `rating` | FLOAT | 0.0 – 5.0 |
| `metacritic` | FLOAT | 0 – 100 |
| `genres` | STRING | Separados por `||` |
| `platforms` | STRING | Separados por `||` |
| `developers` | STRING | Separados por `||` |
| `publishers` | STRING | Separados por `||` |
| `esrb_rating` | STRING | Clasificación ESRB |
| `semana` | INT | Semana de carga (1-17) |

## Endpoints FastAPI

| Método | Ruta | Archivo |
|--------|------|---------|
| GET | `/store/featured` | `store/juegos_destacados.py` |
| GET | `/store/new-releases` | `store/nuevos_lanzamientos.py` |
| GET | `/store/popular` | `store/juegos_populares.py` |
| GET | `/store/free-games` | `store/juegos_gratis.py` |
| GET | `/store/games` | `store/listar_juegos.py` |
| GET | `/store/games/{slug}` | `store/detalle_juego.py` ⚠ último en router |

## Estructura del módulo

```
backend/store/
├── router.py              — agrega todos los sub-routers (/{slug} al final)
├── juegos_destacados.py   — GET /store/featured
├── nuevos_lanzamientos.py — GET /store/new-releases
├── juegos_populares.py    — GET /store/popular
├── juegos_gratis.py       — GET /store/free-games
├── listar_juegos.py       — GET /store/games (filtros + paginación)
├── detalle_juego.py       — GET /store/games/{slug} (enriquecido RAWG)
├── calcular_precio.py     — calc_price(), enrich(), placeholder_image(), to_store()
├── cliente_rawg.py        — get_media(slug) → GameMediaDTO
├── filtros.py             — (filtros auxiliares)
├── generos.py             — (listado de géneros disponibles)
└── modelos_store.py       — StoreGameDTO, StorePageDTO, StoreGameDetailDTO, GameMediaDTO
```

## Criterios de ordenamiento (listar_juegos.py)

| order_by | SQL generado |
|----------|-------------|
| `rating` (defecto) | `rating DESC` |
| `metacritic` | `metacritic DESC` |
| `released` | `released_ts DESC` |
| `name` | `name ASC` |
| `price_asc` | `rating ASC, metacritic ASC` |
| `price_desc` | `rating DESC, metacritic DESC` |

## Flujo de enriquecimiento RAWG

```
GET /store/games
→ pinot_query(...) → lista de VideoGameDTO
→ asyncio.gather(*[get_media(g.slug) for g in games])
→ para cada juego: to_store(g, media.background_image or placeholder_image(g.name))
→ retorna list[StoreGameDTO] enriquecidos
```

## Flujo de detalle (asyncio.gather)

```
GET /store/games/{slug}
→ pinot_query por slug → base VideoGameDTO
→ asyncio.gather(
     get_media(slug),          -- RAWG: imagen + descripción + screenshots
     pinot_query(similar_sql)  -- 4 juegos del mismo género
   )
→ StoreGameDetailDTO
```

## Componentes Angular

| Componente | Ruta |
|------------|------|
| `StoreHomeComponent` | `/store` |
| `StoreCatalogComponent` | `/store/catalog` |
| `StoreGameDetailComponent` | `/store/game/:slug` |

## Servicio Angular
- `StoreService` — métodos: `getFeatured()`, `getNewReleases()`, `getPopular()`, `getFreeGames()`, `getGames(params)`, `getGameBySlug(slug)`.
