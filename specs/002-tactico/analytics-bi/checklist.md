# Checklist de Validación — Analytics BI y Pipeline ETL

## Pipeline ETL
- [ ] Scripts 00-09 ejecutan sin error en orden secuencial
- [ ] `fact_videogames` tiene > 1,000,000 registros tras la carga
- [ ] Las 5 dimensiones existen en Pinot OFFLINE
- [ ] Los 3 topics Kafka REALTIME existen y son consumidos por Pinot

## Servidor ETL
- [ ] `etl_server.py` responde en puerto 5001
- [ ] Endpoints del servidor disparan scripts correctamente

## Integridad de datos
- [ ] Schemas Pinot en `etl/pinot_schemas/` cubren todos los campos del código
- [ ] El campo `semana` está presente en todos los registros de `fact_videogames`
- [ ] `deleteRecordColumn` configurado en tablas REALTIME para soportar tombstone

## Cumplimiento de principios
- [ ] P6: campo `semana` presente y filtros funcionan con `semana <= N`
- [ ] P1: las tablas REALTIME consumen de Kafka (no ingesta directa)
