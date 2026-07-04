# Plan Técnico — Analytics BI y Pipeline ETL

## Scripts ETL (numerados, ejecutar en orden)

| Script | Descripción |
|--------|-------------|
| `00_create_collection.py` | Crea colecciones base (legacy PocketBase — puede omitirse) |
| `01_upload_to_pocketbase.py` | Upload inicial (legacy — puede omitirse) |
| `02_extract_to_parquet.py` | Extrae de RAWG API y genera Parquet en `etl/data/` |
| `03_load_to_pinot.py` | Carga Parquet a Pinot OFFLINE (`fact_videogames`) |
| `04_ingest_pinot.py` | Ingesta adicional a Pinot OFFLINE |
| `05_create_empresa_tables.py` | Crea schemas de tablas empresariales |
| `06_populate_empresa_tables.py` | Pobla colecciones empresariales iniciales |
| `07_create_dimensions.py` | Crea y carga las 5 dimensiones OFFLINE |
| `08_create_realtime_tables.py` | Crea topics Kafka + tablas REALTIME en Pinot |
| `09_populate_empresa_pinot.py` | Recarga emp_records en Pinot REALTIME |

## Servidor ETL
- **Flask** en `etl/etl_server.py` — puerto 5001
- Endpoints para disparar scripts remotamente

## Tablas creadas por el ETL

### OFFLINE
- `fact_videogames` — catálogo principal (~1.7 M)
- `dim_generos`, `dim_plataformas`, `dim_desarrolladores`, `dim_publicadores`, `dim_esrb`

### REALTIME
- `fact_users` — usuarios (key: user_id)
- `fact_wishlist` — wishlist (key: wishlist_id = user_id + game_slug)
- `emp_records` — colecciones empresariales (key: record_id)

## Schemas Pinot
Ubicados en `etl/pinot_schemas/`
