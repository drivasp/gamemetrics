# Plan Técnico — Administración de Plataforma

## Tablas Pinot utilizadas
- **emp_records** (REALTIME): `record_id`, `collection`, `data_json`, `deleted`, `created_at`
- **dim_generos, dim_plataformas, dim_desarrolladores, dim_publicadores, dim_esrb** (OFFLINE): solo lectura

## Endpoints FastAPI implementados

| Método | Ruta | Archivo |
|--------|------|---------|
| GET | `/empresa/{collection}/records` | `empresa/endpoints.py` |
| POST | `/empresa/{collection}/records` | `empresa/endpoints.py` |
| PATCH | `/empresa/{collection}/records/{id}` | `empresa/endpoints.py` |
| DELETE | `/empresa/{collection}/records/{id}` | `empresa/endpoints.py` |
| GET | `/dimensiones/*` | `dimensiones/router.py` |

## Colecciones válidas
`plataformas`, `generos`, `clasificaciones_esrb`, `desarrolladores`, `publicadores`, `empleados`, `contratos`, `catalogo_distribucion`, `campanas_marketing`, `evaluaciones_analiticas`

## Flujo de escritura (P1)
```
Administrador → POST /empresa/{col}/records
→ FastAPI genera record_id (uuid4 hex 15 chars)
→ kafka_send("emp_records", record_id, {record_id, collection, data_json, deleted:false, created_at})
→ Kafka topic emp_records → Pinot REALTIME (upsert por record_id)
→ Disponible en GET tras < 2 s
```

## Componentes Angular
- `EmpresaComponent` — selector de colección + tabla CRUD paginada
- `DimensionesComponent` — listado de dimensiones OFFLINE (solo lectura)
