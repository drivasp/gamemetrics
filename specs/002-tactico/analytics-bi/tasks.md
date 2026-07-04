# Tareas — Analytics BI y Pipeline ETL

- [x] T-ETL-01: Implementar `02_extract_to_parquet.py` (extracción RAWG → Parquet)
- [x] T-ETL-02: Implementar `03_load_to_pinot.py` (Parquet → Pinot OFFLINE)
- [x] T-ETL-03: Implementar `07_create_dimensions.py` (5 dimensiones OFFLINE)
- [x] T-ETL-04: Implementar `08_create_realtime_tables.py` (topics Kafka + tablas REALTIME)
- [x] T-ETL-05: Implementar `etl_server.py` (servidor Flask puerto 5001)
- [x] T-ETL-06: Definir schemas Pinot en `etl/pinot_schemas/`
- [x] T-ETL-07: Implementar endpoints dashboard en `backend/dashboard/`
- [ ] T-ETL-08: Agregar monitoreo de salud del pipeline (healthcheck endpoint)
- [ ] T-ETL-09: Documentar proceso de recarga semanal del catálogo
- [ ] T-ETL-10: Agregar script de validación post-carga (count de registros por tabla)
