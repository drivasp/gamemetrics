# Plan Técnico — BI / Analítica

## Tablas Pinot utilizadas
- **fact_videogames** (OFFLINE): campos `id`, `slug`, `name`, `rating`, `metacritic`, `genres`, `platforms`, `esrb_rating`, `released_ts`, `semana`

## Endpoints FastAPI implementados

| Método | Ruta | Archivo |
|--------|------|---------|
| GET | `/api/dashboard/top-rated` | `dashboard/top_rated.py` |
| GET | `/api/dashboard/por-anio` | `dashboard/por_anio.py` |
| GET | `/api/dashboard/por-genero` | `dashboard/por_genero.py` |
| GET | `/api/dashboard/por-plataforma` | `dashboard/por_plataforma.py` |
| GET | `/api/dashboard/por-esrb` | `dashboard/por_esrb.py` |

## Componentes Angular

| Componente | Ruta |
|------------|------|
| `DashboardComponent` | `/` (raíz) |

## Servicios Angular
- `DashboardService` — consume los 5 endpoints del dashboard con parámetro `semana`.

## Flujo de datos
```
Slider semana (Angular) → DashboardService.getTopRated(semana)
→ GET /api/dashboard/top-rated?semana=N
→ FastAPI: pinot_query("SELECT ... FROM fact_videogames WHERE semana <= N ...")
→ Pinot OFFLINE → JSON response
→ Gráfico renderizado en < 3s
```
