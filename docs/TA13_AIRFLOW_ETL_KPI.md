# TA 13 — Orquestación con Airflow, KPIs pre-agregados y benchmark (GameMetrics S.A.)

**Asignatura:** Construcción del Software · Sexto Semestre
**Proyecto:** GameMetrics S.A.
**Enfoque de datos:** ETL (Extract → Transform → Load) orquestado por **Apache Airflow**
**Stack relevante:** Angular · FastAPI · Apache Kafka · Apache Pinot (BD columnar OLAP, PinotSQL) · Docker · Apache Airflow (LocalExecutor)

---

## 1. Por qué este documento

`docs/TA11_OBJETIVOS_TACTICOS.md` (línea 69) ya dejaba constancia de que el enunciado del curso pide Airflow como orquestador, pero que en ese momento el proyecto lo resolvía con un "equivalente funcional" (panel ETL + scripts Python ejecutados a mano). Este documento cierra esa brecha: agrega Airflow real (carpeta `airflow/`), materializa KPIs pre-agregados en Pinot, y responde con evidencia las preguntas del enunciado: agregar vs. borrar-y-recargar, incompatibilidades de SQL, tiempos de ejecución, mapa OE → dashboards, y necesidad de IA.

---

## 2. Arquitectura de Airflow

```
airflow/                                (compose SEPARADO del docker-compose.yml raíz)
├── docker-compose.yml   → airflow-postgres (metadata propia) + airflow-webserver (:8081) + airflow-scheduler
└── dags/
    ├── common/           → pinot_client.py (SQL + DDL + shim de compatibilidad), kafka_client.py, etl_loader.py
    ├── dag_bootstrap_ddl.py                → manual   → crea report_kpi_partners_resumen / report_kpi_ventas_diarias
    ├── dag_etl_catalogo_videogames.py      → @daily   → extract/transform/load próxima semana → fact_videogames
    ├── dag_etl_comercial_realtime.py       → cada 6h  → agrega ventas nuevas al ledger B2B (incremental)
    └── dag_kpi_reportes.py                 → @hourly  → agrega KPIs + benchmark tradicional vs. pre-agregado
```

El Postgres de Airflow es **exclusivamente su metastore interno** (estado de DAGs/tasks) — no almacena ningún dato de negocio de GameMetrics, que sigue viviendo 100% en Pinot, respetando la restricción arquitectónica del README ("no hay PostgreSQL, MongoDB ni Redis" para datos de negocio).

### Lista de DAGs y frecuencia (lo que pide el enunciado)

| DAG | Schedule | Qué hace | Fase ETL |
|---|---|---|---|
| `gamemetrics_bootstrap_ddl` | Manual (`schedule=None`) | Crea/repara las 2 tablas Pinot KPI nuevas | DDL, no ETL recurrente |
| `gamemetrics_etl_catalogo_videogames` | `@daily` | Carga la siguiente "semana" del catálogo a `fact_videogames` | Extract → Transform → Load (3 tasks separadas) |
| `gamemetrics_etl_comercial_realtime` | `0 */6 * * *` | Agrega ventas nuevas al ledger B2B vía Kafka | Extract → Transform → Load |
| `gamemetrics_kpi_reportes` | `@hourly` | Materializa KPIs + corre el benchmark | Extract → Transform → Load → Benchmark |

Cada DAG se activa/desactiva y se dispara manualmente desde la UI (`http://localhost:8081`, usuario `admin`/`admin`).

---

## 3. ¿Conviene agregar registros o borrar y volver a cargar?

Respuesta corta: **depende de qué tabla es**, y ningún DAG programado hace un `wipe` completo.

| Tipo de tabla | Ejemplo | Política aplicada | Por qué |
|---|---|---|---|
| Hechos transaccionales (ventas, órdenes) | `fact_partner_ledger` | **Incremental / append puro**, `ledger_entry_id` único por evento (uuid4) | Un DAG que corre cada 6h no puede borrar ventas reales en cada corrida — perdería historia. |
| KPI pre-agregados (resúmenes) | `report_kpi_partners_resumen`, `report_kpi_ventas_diarias` | **Upsert por clave de negocio** (`partner_id`, `fecha`) vía `upsertConfig` de Pinot (ya usado en el proyecto: "borrado lógico, no DELETE físico") | El KPI debe reflejar el estado *actual*; upsert evita tanto duplicar filas como tener que dropear/recrear la tabla en cada corrida. |
| Reset administrativo total | `fact_partner_accounts`, `fact_partner_ledger`, etc. (patrón de `etl/22_wipe_business_demo_data.py`) | **Wipe manual, fuera de cualquier DAG programado** | Solo tiene sentido para reiniciar una demo o tras un cambio de esquema; automatizarlo borraría datos reales en producción. |

`etl/24_seed_reports_demo.py` (agrega sin dedupe real) y `etl/22_wipe_business_demo_data.py` (borra todo) ya existían como los dos extremos; los DAGs nuevos toman **la tercera opción** (upsert por clave) para las tablas KPI, que es la que de verdad corresponde a un pipeline recurrente.

---

## 4. Incompatibilidades de SQL en Pinot (PinotSQL ≠ SQL estándar)

Apache Pinot no es un RDBMS: expone **PinotSQL** vía `POST /query/sql`, con dos motores de ejecución:

- **Single-stage engine** (por defecto): rápido, pero **no soporta JOIN entre tablas** de forma confiable.
- **Multi-stage engine** (`useMultistageEngine=true`): soporta JOIN, pero debe pedirse explícitamente por query.

`airflow/dags/common/pinot_client.py::run_sql_compatible()` implementa el patrón exacto que pide el enunciado ("en caso de incompatibilidad, buscar una versión compatible"):

1. Intenta la consulta preferida (un `JOIN` real entre `fact_partner_ledger` y `fact_partner_accounts`, con el motor multi-stage habilitado).
2. Si el broker devuelve `exceptions` en el body (Pinot responde HTTP 200 con errores dentro del JSON, no un 4xx), cae automáticamente a la alternativa compatible: dos `SELECT` de tabla única + merge en Python — el mismo patrón que ya usa hoy `backend/checkout/partner_ledger.py::admin_business_dashboard`.
3. El DAG `gamemetrics_kpi_reportes` corre esto en su primera task, `sql_compat_check`, y loguea qué ruta (`preferred` o `fallback`) funcionó contra el Pinot 1.0.0 real de este stack.

**Resultado observado (corrida real, `manual__2026-08-16T15:00:00+00:00` y siguientes):** ruta **`preferred`** — el broker de Pinot 1.0.0 de este stack acepta el `JOIN` con `useMultistageEngine=true` sin excepciones (10 filas devueltas, motor multi-stage disponible por defecto en esta instalación). El shim de compatibilidad (`run_sql_compatible()`) no tuvo que activar el fallback en este entorno, pero queda en el código como salvaguarda para despliegues donde el motor multi-stage esté deshabilitado o la versión de Pinot sea anterior a 1.0 (donde JOIN no existe en absoluto).

**Incompatibilidad real que sí apareció (y se resolvió) al construir la imagen de Airflow — no en PinotSQL sino en el propio `pip install`:**

1. `httpx==0.27.2` (pineado a mano) chocaba con el `constraints-2.10.4/constraints-3.12.txt` oficial de Airflow, que exige `httpx==0.27.0` → `ResolutionImpossible`.
2. Corregido el primero, el mismo problema reapareció con `pandas==2.2.3` vs. `pandas==2.1.4` del constraints file.
3. **Versión compatible aplicada:** dejar de pinear `httpx`/`pandas`/`pyarrow` en `airflow/requirements.txt` y dejar que `pip` resuelva contra el constraints file oficial (`--constraint ".../constraints-3.12.txt"`), que es justamente la práctica recomendada por Airflow para evitar este tipo de conflicto.
4. Un tercer conflicto, ya en tiempo de ejecución (no de build): `kafka-python==2.0.2` (la misma versión que usa `etl/`) lanza `ModuleNotFoundError: No module named 'kafka.vendor.six.moves'` bajo Python 3.12 (la imagen base de Airflow). **Versión compatible aplicada:** `kafka-python-ng==2.2.3`, el fork mantenido por la comunidad que expone el mismo paquete `kafka` pero sí soporta 3.12+.

Ver `airflow/requirements.txt` y `airflow/Dockerfile` para el detalle.

---

## 5. Tablas Pinot nuevas para informes compuestos

| Tabla | Grano | Alimentada por | Reemplaza (agregación en caliente) |
|---|---|---|---|
| `report_kpi_partners_resumen` | 1 fila por partner | `gamemetrics_kpi_reportes` (hourly) | `admin_business_dashboard` / `platform_gmv_summary`, usada hoy por GM-C01/GM-C03 |
| `report_kpi_ventas_diarias` | 1 fila por día | `gamemetrics_kpi_reportes` (hourly) | No existía — habilita el primer filtro de **rango de fechas** del Centro de Reportes |

Nuevos informes en el Centro de Reportes (`backend/reports/`, visibles en `/reports`):

- **GM-C08 — Ventas diarias (KPI pre-agregado)**: filtros `date_from` / `date_to`, fuente `report_kpi_ventas_diarias`.
- **GM-C09 — Resumen de estudios (KPI pre-agregado)**: gemelo directo de GM-C03, fuente `report_kpi_partners_resumen`, usado como sujeto del benchmark de la §6.

---

## 6. Informe tradicional (SQL en caliente) vs. informe vía Airflow (pre-agregado)

### Qué se compara

- **Tradicional**: `airflow/reports_output/run_informe_tradicional.py` — SELECT crudo sobre `fact_partner_ledger` (hasta 5000 filas) + agregación en un loop de Python, **exactamente** el patrón que usa hoy GM-C01/GM-C03 en producción. Corre standalone, sin Airflow.
- **Vía Airflow**: la task `benchmark_vs_tradicional` del DAG `gamemetrics_kpi_reportes` repite la misma agregación (para tener el punto de comparación "justo") y la compara contra un `SELECT` simple sobre `report_kpi_partners_resumen`, la tabla que el propio DAG acaba de materializar.

### Cómo reproducir

```powershell
# 1) Stack principal + Airflow arriba
docker compose up -d               # (raíz del proyecto)
cd airflow
copy .env.example .env
docker compose up -d airflow-init
docker compose up -d

# 2) Disparar los DAGs (UI en http://localhost:8081, admin/admin)
#    gamemetrics_bootstrap_ddl  -> una vez, crea las tablas KPI
#    gamemetrics_kpi_reportes   -> materializa KPIs + corre el benchmark

# 3) Informe tradicional standalone (fuera de Airflow)
cd reports_output
python run_informe_tradicional.py
```

### Resultados (medición real, stack local — 204 filas en `fact_partner_ledger`, 10 partners con ventas)

| Medición | Tiempo (s) | Filas escaneadas | Fuente |
|---|---|---|---|
| Informe tradicional (`run_informe_tradicional.py`, standalone desde el host) | **0.6524** | 204 (ledger) + 29 (accounts) | `fact_partner_ledger` (crudo) |
| Task `benchmark_vs_tradicional` → rama "tradicional" (dentro del contenedor Airflow) | **0.1779** | 204 | `fact_partner_ledger` (crudo) |
| Task `benchmark_vs_tradicional` → rama "pre-agregado" | **0.0617** | 10 | `report_kpi_partners_resumen` |
| **Speedup** (tradicional in-container / pre-agregado) | **2.88×** | 204 → 10 filas | `airflow/reports_output/benchmark_manual__2026-08-16T16:10:26+00:00.json` |

El script standalone (0.65 s) es más lento que la rama "tradicional" corrida dentro del contenedor de Airflow (0.18 s) pese a hacer exactamente las mismas dos consultas — la diferencia es el salto host-Windows → Docker Desktop → contenedor por el puerto publicado `localhost:8099`, contra la latencia contenedor-a-contenedor dentro de la red `gamemetrics`. Es un dato real y esperable, no un error de medición: confirma que además de "cuántas filas escanea la query", la topología de red también pesa — otra razón por la que corridas programadas dentro del propio clúster (Airflow) son más consistentes que un script disparado ad hoc desde la máquina del desarrollador.

**Lectura esperada (y el punto pedagógico central visto en clase):** el `SELECT` sobre la tabla pre-agregada escanea un puñado de filas (una por partner, 10) contra las 204 filas de ledger crudo — con solo 204 filas el speedup ya es de casi 3×; la diferencia crece con el volumen de datos, no con la complejidad de la query, así que en producción (miles/millones de filas de ledger) la brecha sería mucho mayor. Esto es exactamente por qué un pipeline ETL con materialización (modelo en estrella / agregados precomputados) es la práctica correcta para BI, en vez de recalcular sobre hechos crudos en cada request.

### Tiempo de ejecución de cada DAG (Airflow)

Se mide de dos formas complementarias:

1. **UI de Airflow** (`/dags/<dag_id>/grid`, vista Gantt): duración nativa por task y por DAG run — no requiere instrumentación adicional.
2. **Log estructurado**: cada corrida de `gamemetrics_kpi_reportes` deja un archivo `airflow/reports_output/benchmark_<run_id>.json` con marca de tiempo, dando una serie histórica en vez de una sola medición puntual.

| DAG | Duración total (corrida real medida) | Cómo se obtuvo |
|---|---|---|
| `gamemetrics_bootstrap_ddl` | **9.1 s** (2 tablas: schema+table cada una) | `airflow dags list-runs` / Grid view |
| `gamemetrics_etl_catalogo_videogames` | **19.1 s** (extract 4.7 s + transform 2.7 s + load a Pinot) | `airflow dags list-runs` / Grid view |
| `gamemetrics_etl_comercial_realtime` | **7.5 s** (extract + transform + publicar a Kafka) | `airflow dags list-runs` / Grid view |
| `gamemetrics_kpi_reportes` | **12.4 s** (incluye `sql_compat_check` + extract + transform + load + benchmark) | `airflow dags list-runs` + `benchmark_<run_id>.json` |

A esta escala de datos (demo académica: cientos de filas de ledger, 29 partners, catálogo por semana), los 4 DAGs corren en segundos — el costo dominante no es la agregación en sí sino la conexión/consulta a Pinot y la publicación a Kafka. La UI de Airflow (`/dags/<dag_id>/grid`) permite ver esta misma información desglosada por task y comparar corridas históricas sin tener que instrumentar nada adicional.

---

## 7. Mapa OE → Dashboards

Los 4 objetivos estratégicos (Balanced Scorecard) están definidos en `README.md`:

| OE | Objetivo | Dashboards / informes que lo cubren |
|---|---|---|
| **OE1** | Penetración de mercado digital (registro, tienda, wishlist) | GM-S10 (biblioteca/compras), GM-S11 (elegibles a reembolso), GM-C04/C05/C06/C07 (catálogo por semana, género, plataforma, top rating) |
| **OE2** | Escalabilidad comercial (APIs, reseñas verificadas, regalos) | GM-S09 (featured activos), GM-S12/S13 (claims y payouts por estudio), **GM-C09 nuevo** (resumen de estudios pre-agregado) |
| **OE3** | Infraestructura cloud contenerizada (Docker Compose, ETL, HA) | GM-S06 (estado de jobs ETL), Grid/Gantt de Airflow (`localhost:8081`), tiempos de §6 de este documento |
| **OE4** | Inteligencia de negocio centralizada (modelo estrella, KPIs) | GM-C01/C02/C03 (economía B2B en caliente) + **GM-C08/GM-C09 nuevos** (KPI pre-agregados vía Airflow) — el par que demuestra el "antes/después" del modelo en estrella |

---

## 8. ¿Se necesita Inteligencia Artificial?

**No es obligatoria según los objetivos del proyecto.** Ninguno de los 4 objetivos estratégicos (OE1–OE4, README) exige IA/ML — se centran en penetración de mercado, escalabilidad comercial, infraestructura cloud y BI centralizada mediante **modelo en estrella + KPIs**, no en modelos predictivos. Tampoco lo exige `docs/TA11_OBJETIVOS_TACTICOS.md`.

**Conclusión aplicada a este entregable:** no se implementa ningún método de IA/ML. El roadmap del `README.md` ya contempla como ítem de trabajo *futuro* (no obligatorio, no bloqueante) "Modelos ML (recomendaciones, abandono wishlist)" — si en una fase posterior un OE explícito lo exigiera (p. ej. un OE5 de "personalización predictiva"), los candidatos naturales serían: forecasting simple de GMV diario sobre `report_kpi_ventas_diarias` (ya materializado, listo como feature store mínimo) y un modelo de abandono de wishlist sobre `fact_wishlist_price_alerts` + `fact_user_events`. Ninguno se construye aquí porque no es obligatorio.

---

## 9. Evidencia en el repositorio

| Área | Ruta |
|---|---|
| Infraestructura Airflow | `airflow/docker-compose.yml`, `airflow/Dockerfile` |
| DAGs | `airflow/dags/dag_*.py` |
| Cliente Pinot + shim de compatibilidad | `airflow/dags/common/pinot_client.py` |
| Tablas Pinot nuevas | `etl/pinot_schemas/{schema,table}_report_kpi_*.json` |
| Informes nuevos | `backend/reports/catalog.py` (GM-C08/GM-C09), `backend/reports/service.py` |
| Filtro de fecha en frontend | `frontend/videogames-dashboard/src/app/components/reports/report-viewer.component.{ts,html,scss}` |
| Informe tradicional standalone | `airflow/reports_output/run_informe_tradicional.py` |
| Política agregar vs. wipe (script de referencia) | `etl/22_wipe_business_demo_data.py`, `etl/24_seed_reports_demo.py` |

---

**Nota:** convertir este documento a PDF para la entrega del aula virtual, igual que TA11 (Word → Exportar PDF, o VS Code Markdown PDF), una vez completadas las secciones §4 y §6 con los valores medidos en el entorno real.
