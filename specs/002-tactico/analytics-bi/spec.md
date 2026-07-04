# Nivel Táctico — Analytics BI y Pipeline ETL

## 1. Nombre del paquete
**Analytics BI** — Pipeline ETL, Carga de Datos y Análisis de KPIs

## 2. Objetivo
Gestionar el pipeline de extracción, transformación y carga (ETL) que alimenta el catálogo analítico OFFLINE de Pinot, y proveer los endpoints de análisis KPI consumidos por el nivel estratégico.

## 3. Contexto
El catálogo de ~1.7 M de videojuegos proviene de la RAWG API y se carga periódicamente a Pinot OFFLINE vía archivos Parquet. Los scripts ETL numerados (`00` a `09`) ejecutan cada etapa del pipeline. El servidor ETL (`etl_server.py`) expone endpoints para disparar scripts remotamente.

## 4. Ubicación
- **Nivel empresarial:** Táctico (002)
- **Departamento:** Analytics BI
- **Paquetes:** etl (pipeline), dashboard (KPIs)

## 5. Actores

| Actor | Rol |
|-------|-----|
| Administrador ETL | Ejecuta y monitorea el pipeline ETL. |
| Sistema (ETL) | Extrae de RAWG, genera Parquet, carga a Pinot OFFLINE. |
| Analista BI | Consume los KPIs resultantes del ETL. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-T12 | Ejecutar pipeline ETL completo (scripts 00-09) | Administrador ETL | OE4 |
| CU-T13 | Crear tablas REALTIME en Pinot (script 08) | Administrador ETL | OE4 |
| CU-T14 | Cargar datos OFFLINE a Pinot (scripts 03-04) | Administrador ETL | OE4 |
| CU-T15 | Consultar KPIs derivados del catálogo OFFLINE | Analista BI | OE1 |
| CU-T16 | Recargar dimensiones empresariales (script 09) | Administrador ETL | OE3, OE4 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-ETL-001 | Como Administrador ETL, quiero ejecutar el script 03 para cargar datos Parquet a Pinot OFFLINE sin interrumpir la tienda. |
| US-ETL-002 | Como Administrador ETL, quiero crear las tablas REALTIME (script 08) para que el backend pueda escribir usuarios y wishlist. |
| US-ETL-003 | Como Analista BI, quiero que los KPIs del dashboard reflejen el catálogo más reciente tras cada carga ETL. |
| US-ETL-004 | Como Administrador ETL, quiero que el servidor ETL exponga endpoints para ejecutar scripts sin acceso SSH directo. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-ETL-001 | El sistema MUST proveer un servidor Flask (`etl_server.py`) que exponga endpoints para disparar scripts ETL remotamente. |
| RF-ETL-002 | El script `08_create_realtime_tables.py` MUST crear los topics Kafka y tablas Pinot REALTIME para `fact_users`, `fact_wishlist` y `emp_records`. |
| RF-ETL-003 | El script `03_load_to_pinot.py` MUST cargar archivos Parquet a la tabla OFFLINE `fact_videogames`. |
| RF-ETL-004 | Los scripts ETL MUST ser ejecutables de forma secuencial (`00` → `09`) para una carga inicial completa. |
| RF-ETL-005 | El pipeline MUST generar los archivos de schemas Pinot en `etl/pinot_schemas/` antes de crear las tablas. |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-ETL-001 | La carga completa de 1.7 M de registros a Pinot OFFLINE SHOULD completarse en menos de 30 minutos. |
| RNF-ETL-002 | El servidor ETL MUST correr en un contenedor Docker independiente (no en el mismo que FastAPI). |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-ETL-001 | Las tablas OFFLINE son inmutables entre cargas; no se actualizan en tiempo real. |
| RN-ETL-002 | Cada carga ETL asigna un número de `semana` incremental a los registros nuevos. |
| RN-ETL-003 | Los schemas Pinot deben definirse antes de crear las tablas (scripts de schema primero). |

## 11. Entradas y salidas

| Elemento | Descripción |
|----------|-------------|
| **Entrada** | Datos de RAWG API (JSON) o archivos Parquet existentes en `etl/data/`. |
| **Salida** | Tablas Pinot OFFLINE (`fact_videogames`, dimensiones) y REALTIME (`fact_users`, `fact_wishlist`, `emp_records`). |

## 12. Escenarios Gherkin

**Escenario: Carga inicial del sistema**
```gherkin
Dado que los contenedores de Kafka y Pinot están corriendo
Y el Administrador ETL ejecuta los scripts en orden 00 → 09
Cuando cada script completa sin error
Entonces la tabla fact_videogames tiene datos en Pinot OFFLINE
Y las tablas fact_users, fact_wishlist, emp_records existen en Pinot REALTIME
Y los topics Kafka fact_users, fact_wishlist, emp_records existen
```

**Escenario: Recarga de dimensiones**
```gherkin
Dado que las dimensiones necesitan actualizarse
Cuando el Administrador ETL ejecuta el script 09
Entonces los registros de emp_records se recargan en Pinot REALTIME
Y las dimensiones OFFLINE se mantienen sin cambio
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-ETL-001 | Tras ejecutar scripts 00-09, `SELECT COUNT(*) FROM fact_videogames` en Pinot retorna > 1,000,000. |
| CA-ETL-002 | Los topics Kafka `fact_users`, `fact_wishlist`, `emp_records` existen en el broker. |
| CA-ETL-003 | El servidor ETL responde en el puerto 5001. |
| CA-ETL-004 | Las 5 dimensiones OFFLINE existen en Pinot tras ejecutar script 07. |

## 14. Dependencias

| Paquete | Tipo |
|---------|------|
| Apache Pinot (broker:8099, controller:9000) | Destino de la carga. |
| Apache Kafka (kafka:9092) | Topics REALTIME. |
| RAWG API | Fuente de datos del catálogo. |

## 15. Fuera de alcance

- CI/CD automático del pipeline ETL (planificado con GitHub Actions).
- Ingesta incremental en tiempo real desde RAWG (actualmente es batch semanal).
- Monitoreo de la salud del pipeline con alertas automáticas.
