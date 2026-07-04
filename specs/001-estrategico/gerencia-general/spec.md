# Nivel Estratégico — Gerencia General

## 1. Nombre del paquete
**BI / Analítica** — Inteligencia de Negocio y Dashboards KPI

## 2. Objetivo
Proveer a la dirección y analistas de GameMetrics S.A. una visión consolidada del catálogo de videojuegos mediante KPIs interactivos y gráficos analíticos filtrados por semana (1-17), permitiendo decisiones estratégicas basadas en datos reales del catálogo OFFLINE (~1.7 M títulos).

## 3. Contexto
El negocio necesita entender tendencias del mercado de videojuegos: qué géneros dominan, qué plataformas son más populares, cómo se distribuyen los juegos por clasificación ESRB y cómo evoluciona el catálogo por año de lanzamiento. Apache Pinot OFFLINE permite consultas analíticas sub-segundo sobre millones de registros.

## 4. Ubicación
- **Nivel empresarial:** Estratégico (001)
- **Departamento:** Gerencia General / Inteligencia de Negocio
- **Paquete:** BI / Analítica (dashboard)

## 5. Actores

| Actor | Rol |
|-------|-----|
| Analista BI | Consume dashboards y filtra por semana/dimensiones. |
| Visitante | Puede ver el dashboard en modo lectura sin autenticación. |
| Administrador | Supervisa la integridad de los datos analíticos. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-E01 | Ver KPIs generales del catálogo | Analista BI, Visitante | OE1, OE4 |
| CU-E02 | Filtrar por semana de carga (slider 1-17) | Analista BI | OE1, OE4 |
| CU-E03 | Ver top juegos mejor valorados | Analista BI, Visitante | OE1 |
| CU-E04 | Ver distribución por género | Analista BI, Visitante | OE1 |
| CU-E05 | Ver distribución por plataforma | Analista BI, Visitante | OE1 |
| CU-E06 | Ver distribución por clasificación ESRB | Analista BI, Visitante | OE1 |
| CU-E07 | Ver juegos por año de lanzamiento | Analista BI, Visitante | OE1 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-BI-001 | Como Analista BI, quiero ver el total de juegos en el catálogo para conocer la cobertura de datos. |
| US-BI-002 | Como Analista BI, quiero filtrar todos los gráficos por semana (1-17) para analizar la evolución temporal del catálogo. |
| US-BI-003 | Como Analista BI, quiero ver el top 10 de juegos mejor valorados (rating + metacritic) para identificar títulos de referencia. |
| US-BI-004 | Como Analista BI, quiero ver un gráfico de distribución por género para identificar géneros dominantes. |
| US-BI-005 | Como Analista BI, quiero ver la distribución por plataforma para entender el mercado de hardware. |
| US-BI-006 | Como Analista BI, quiero ver la distribución por clasificación ESRB para analizar el perfil demográfico del catálogo. |
| US-BI-007 | Como Visitante, quiero ver los dashboards sin necesidad de registrarme para explorar la plataforma. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-BI-001 | El sistema MUST proveer un endpoint `GET /api/dashboard/top-rated?semana=N` que retorne los top juegos ordenados por metacritic DESC. |
| RF-BI-002 | El sistema MUST proveer un endpoint `GET /api/dashboard/por-genero?semana=N` que retorne conteo de juegos agrupado por género. |
| RF-BI-003 | El sistema MUST proveer un endpoint `GET /api/dashboard/por-plataforma?semana=N` que retorne conteo de juegos agrupado por plataforma. |
| RF-BI-004 | El sistema MUST proveer un endpoint `GET /api/dashboard/por-esrb?semana=N` que retorne conteo de juegos agrupado por clasificación ESRB. |
| RF-BI-005 | El sistema MUST proveer un endpoint `GET /api/dashboard/por-anio?semana=N` que retorne conteo de juegos agrupado por año de lanzamiento. |
| RF-BI-006 | Todos los endpoints de dashboard SHALL filtrar con `WHERE semana <= N` sobre `fact_videogames` (tabla OFFLINE). |
| RF-BI-007 | El dashboard Angular MUST mostrar un slider que controle el parámetro `semana` (valores 1-17) y refresque todos los gráficos al cambiar. |
| RF-BI-008 | Los dashboards MUST ser accesibles sin autenticación (Visitante). |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-BI-001 | Los endpoints de KPIs MUST responder en menos de 2 segundos sobre 1.7 M de registros en Pinot OFFLINE. |
| RNF-BI-002 | Los endpoints de gráficos MUST responder en menos de 3 segundos. |
| RNF-BI-003 | El frontend SHOULD mostrar un indicador de carga durante las consultas analíticas. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-BI-001 | El filtro por semana usa `semana <= N`, no `semana = N`, para incluir acumulado histórico. |
| RN-BI-002 | Los datos del catálogo son OFFLINE e inmutables entre cargas ETL; no reflejan cambios en tiempo real. |
| RN-BI-003 | El slider de semanas va de 1 a 17 (rango del catálogo cargado). |

## 11. Entradas y salidas

| Elemento | Descripción |
|----------|-------------|
| **Entrada** | Parámetro `semana` (int, 1-17) via query string. |
| **Salida** | JSON con listas de pares `{nombre, conteo}` o `{nombre, rating, metacritic}`. |

## 12. Escenarios Gherkin

**Escenario: Analista filtra dashboard por semana 10**
```gherkin
Dado que el Analista BI está en el dashboard
Y el slider de semana está en 10
Cuando el sistema consulta GET /api/dashboard/por-genero?semana=10
Entonces el servidor consulta Pinot con WHERE semana <= 10
Y retorna un JSON con conteo de juegos por género en menos de 3 segundos
```

**Escenario: Dashboard sin autenticación**
```gherkin
Dado que un Visitante accede a la URL raíz del frontend
Cuando carga la página principal
Entonces ve los KPIs del catálogo sin necesidad de token JWT
```

**Escenario: Semana fuera de rango**
```gherkin
Dado que el parámetro semana = 0
Cuando el endpoint procesa la consulta
Entonces retorna resultados vacíos o el comportamiento por defecto (semana=1)
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-BI-001 | El endpoint `/api/dashboard/top-rated?semana=17` retorna al menos 10 registros en menos de 2 s. |
| CA-BI-002 | El slider al valor 5 provoca que todos los gráficos se recarguen con datos de semanas 1-5. |
| CA-BI-003 | Un Visitante sin token puede acceder al dashboard sin redirección de login. |
| CA-BI-004 | Los 5 endpoints de dashboard responden HTTP 200 con JSON válido. |

## 14. Dependencias

| Paquete | Tipo |
|---------|------|
| ETL (002-tactico/analytics-bi) | Upstream: genera los datos OFFLINE que este paquete consulta. |
| Dimensiones (002-tactico/administracion) | Metadatos de géneros, plataformas, ESRB usados en gráficos. |
| `shared/cliente_pinot.py` | Dependencia técnica: cliente de consultas Pinot. |

## 15. Fuera de alcance

- Modelos de ML / forecasting (roadmap futuro).
- Exportación de reportes a Excel/PDF.
- Dashboards en tiempo real basados en fact_users o fact_wishlist.
- Segmentación avanzada y análisis de abandono de wishlist (roadmap).
