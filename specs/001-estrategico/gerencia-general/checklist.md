# Checklist de Validación — BI / Analítica

## Calidad de código
- [ ] Todos los endpoints usan `pinot_query()` del shared client
- [ ] Parámetro `semana` siempre validado como `int` con valor por defecto (17)
- [ ] Ningún endpoint escribe datos (solo lectura de OFFLINE)
- [ ] `response_model` explícito en cada endpoint FastAPI

## Funcionalidad
- [ ] GET `/api/dashboard/top-rated?semana=17` retorna ≥ 10 registros
- [ ] Todos los endpoints filtran con `WHERE semana <= N`
- [ ] El slider en el frontend actualiza todos los gráficos al moverse
- [ ] El dashboard carga sin autenticación (sin token JWT)

## Rendimiento
- [ ] Tiempo de respuesta < 2 s para KPIs en el entorno Docker Compose
- [ ] Tiempo de respuesta < 3 s para gráficos

## Cumplimiento de principios
- [ ] P6: uso de `semana <= N` (no `semana = N`)
- [ ] P5: no hay claves de API ni secretos en el frontend
- [ ] P3: no hay referencias a PocketBase
