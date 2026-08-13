# TA 11 — Objetivos tácticos e informes (GameMetrics S.A.)

**Asignatura:** Construcción del Software · Sexto Semestre  
**Proyecto:** GameMetrics S.A.  
**Enfoque de datos:** **ETL** (Extract → Transform → Load)  
**Stack relevante:** Angular · FastAPI · Apache Kafka · Apache Pinot (BD columnar OLAP) · Docker  

---

## 1. Contexto del proyecto (fase táctica)

GameMetrics pasa de la **fase operativa** (tienda, auth, carrito, biblioteca, publishers) a la **fase táctica**: controlar departamentos con objetivos medibles y decidir **qué informes** salen de datos operativos “directos” y cuáles requieren **agregación / tratamiento** vía pipeline ETL hacia la BD columnar (Pinot).

### Diferencia con la guía del compañero

| Aspecto | Compañero (guía) | Este proyecto (GameMetrics tuyo) |
|---------|------------------|-----------------------------------|
| Enfoque | Orientado a ELT / PocketBase + Pinot | **ETL** explícito (`etl/`, scripts `00`–`21`) |
| Transaccional | PocketBase | **Kafka → Pinot REALTIME** (sin PocketBase) |
| Analítico | Apache Pinot OLAP | Apache Pinot OFFLINE + REALTIME |
| Catálogo | ~300k registros (su entrega) | Catálogo analítico vía ETL a `fact_videogames` |

> Este informe describe **solo** lo documentado e implementado en el repositorio GameMetrics (specs `002-tactico`, docs de fases, panel admin/partner/ETL).

---

## 2. Criterios usados (según enunciado TA 11)

| Tipo | Definición aplicada a GameMetrics |
|------|-----------------------------------|
| **Informe simple** | Se obtiene con consulta/listado directo sobre datos operativos o colecciones empresariales, **sin** agregaciones complejas ni reproceso ETL. Ej.: listar empleados, listar campañas, listar claims pendientes. |
| **Informe compuesto** | Requiere **agregaciones, cruces o transformación** (pipeline ETL / consultas OLAP en Pinot). Ej.: GMV acumulado, fee de plataforma, juegos por género, earnings por publisher. |

**Destino de datos:**

- Informes simples → sobre todo Pinot **REALTIME** / colecciones `emp_records` y listados B2B.  
- Informes compuestos → Pinot **OFFLINE** (`fact_videogames`, dimensiones) y/o agregados de `fact_partner_ledger` / dashboard admin.

---

## 3. Tabla de análisis (entregable TA 11)

| DEPARTAMENTO | OBJETIVOS TÁCTICOS | ¿ES UN INFORME SIMPLE? | ¿ES UN INFORME COMPUESTO? |
|--------------|--------------------|-------------------------|---------------------------|
| **Administración de Plataforma** | Controlar el personal y la estructura organizacional mediante el CRUD de la colección `empleados` en `emp_records`. | **Sí** — listado/CRUD de empleados (`GET/POST /empresa/empleados/records`). | No |
| **Administración de Plataforma** | Registrar y actualizar contratos empresariales (`contratos`). | **Sí** — listado/CRUD de contratos. | No |
| **Administración de Plataforma** | Mantener catálogos maestros de referencia (plataformas, géneros, ESRB, desarrolladores, publicadores) vía dimensiones y/o `emp_records`. | **Sí** — consulta de dimensiones (`/dimensiones`) y colecciones maestras. | No |
| **Administración de Plataforma** | Ejecutar y monitorear el pipeline ETL (carga Parquet → Pinot OFFLINE, tablas REALTIME, recarga de dimensiones). | **Sí** — estado de jobs / semanas en el panel ETL (`etl_server.py`, dashboard `/`). | Parcialmente **compuesto** si se reporta “registros cargados por semana” con conteos agregados sobre Pinot. |
| **Administración de Plataforma** | Supervisar la economía B2B de la plataforma: GMV, ingresos GameMetrics (take rate) y adeudado a publishers. | No | **Sí** — agregaciones sobre `fact_partner_ledger` (`GET /admin/dashboard`, `/admin/gmv`). |
| **Administración de Plataforma** | Revisar y aprobar/rechazar claims de ownership de juegos (cola tipo Steamworks). | **Sí** — listado de claims `pending` (`GET /admin/game-claims`). | No |
| **Ventas y Marketing** | Gestionar campañas de marketing (`campanas_marketing`). | **Sí** — CRUD de campañas en `/empresa/campanas_marketing/records`. | No |
| **Ventas y Marketing** | Gestionar el catálogo de distribución (`catalogo_distribucion`). | **Sí** — CRUD de catálogo de distribución. | No |
| **Ventas y Marketing** | Aplicar y visualizar precios de juegos según fórmula de pricing (rating/metacritic) en la tienda. | **Sí** — precio por juego en tarjeta/detalle (cálculo por registro). | No (el cálculo es por ítem; no es agregado de ventas). |
| **Ventas y Marketing** | Medir rendimiento comercial con evaluaciones analíticas (`evaluaciones_analiticas`). | **Sí** — listado CRUD de evaluaciones. | **Sí**, cuando se correlacionan evaluaciones con KPIs de catálogo/ventas. |
| **Ventas y Marketing** | Controlar placements destacados de pago (featured) y su prioridad en `/store/featured`. | **Sí** — listado de placements activos por partner. | **Sí** — ranking compuesto editorial + placements pagados en featured. |
| **Analytics BI** | Alimentar el catálogo analítico OFFLINE (`fact_videogames`) mediante ETL desde RAWG → Parquet → Pinot. | No | **Sí** — el resultado de la carga es el dataset analítico agregado por semana. |
| **Analytics BI** | Proveer análisis del catálogo: distribución por género, plataforma, ESRB, top por rating/metacritic. | No | **Sí** — agregaciones OLAP sobre `fact_videogames` + dimensiones (KPIs; dashboard histórico/archivado en código, pipeline sí activo). |
| **Analytics BI** | Monitorear métricas de carga ETL (semanas disponibles, progreso de jobs, tablas creadas). | **Sí** — endpoints/estado del servidor ETL. | **Sí** — si se reporta volumen total de juegos cargados (`COUNT` masivo / por semana). |
| **Publishers / Partner B2B** *(área táctica de control comercial B2B existente en el sistema)* | Que el publisher vea sus juegos reclamados y el estado del claim (pending/approved). | **Sí** — listado en `/my-partner`. | No |
| **Publishers / Partner B2B** | Controlar earnings reales: GMV bruto, fee plataforma, neto, saldo available/pending/paid. | No | **Sí** — agregación del ledger (`partner_earnings_summary` sobre `fact_partner_ledger`). |
| **Publishers / Partner B2B** | Seguir historial de payouts liquidados por admin. | **Sí** — listado de payouts del partner. | No (detalle de movimientos); el **saldo consolidado** es compuesto. |

---

## 4. Lectura de la tabla (cómo se usará en ETL)

1. **Informes simples** se pueden servir consultando datos operativos/REALTIME (listados, CRUD, colas de aprobación) **sin** un job ETL adicional.  
2. **Informes compuestos** se diseñan para la **BD columnar Pinot**, alimentada por el **pipeline ETL** (scripts `etl/00`…`21`, `etl_server.py`) o por agregaciones OLAP sobre hechos (`fact_videogames`, `fact_partner_ledger`).  
3. Airflow (mencionado en el enunciado del curso) orquestaría esos jobs ETL; en el proyecto actual la orquestación práctica está en el **panel ETL + scripts Python** (equivalente funcional para la entrega).

---

## 5. Mapa rápido: de dónde sale cada tipo de informe

```
[Operación / REALTIME]                [ETL]                    [Analítico / OFFLINE + agregados]
empleados, contratos, campañas  ──►  (no requiere ETL)  ──►  Informe SIMPLE
claims admin, listados partner  ──►  (no requiere ETL)  ──►  Informe SIMPLE

RAWG / Parquet / fact_videogames ──►  ETL 00–09           ──►  Informe COMPUESTO (catálogo, KPIs)
ventas ledger / GMV / fees       ──►  agregación OLAP     ──►  Informe COMPUESTO (economía B2B)
```

---

## 6. Evidencia en el repositorio (no inventado)

| Área | Evidencia |
|------|-----------|
| Depts. tácticos | `specs/002-tactico/administracion/spec.md`, `ventas/spec.md`, `analytics-bi/spec.md` |
| Mapa general | `specs/000-sistema-general/spec.md` |
| ETL | carpeta `etl/`, `etl/etl_server.py`, glosario ETL en specs |
| Economía / GMV | `docs/FASE2_GANANCIAS.md`, `docs/FASE_DINERO_LEDGER.md`, UI `/admin` |
| Partner earnings | `docs/FASE_DINERO_LEDGER.md`, UI `/my-partner` |
| Claims | aprobación admin (`/admin/game-claims`) |

---

## 7. Conclusión

Para GameMetrics, la fase táctica queda cubierta por tres departamentos formales (**Administración**, **Ventas/Marketing**, **Analytics BI**) más el control B2B de **publishers**, ya presente en el sistema.  

Los **informes simples** sostienen la gestión diaria (CRUD y colas). Los **informes compuestos** justifican el uso de **ETL + Pinot columnar** (catálogo masivo y economía agregada). Esa separación es la base para decidir qué se consulta “en caliente” y qué se materializa en la BD columnar.

---

**Autor del proyecto:** según documentación del repo (GameMetrics S.A. · Construcción de Software).  
**Nota:** Convertir este documento a PDF para la entrega del aula virtual (Word → Exportar PDF, o VS Code Markdown PDF).
