# GameMetrics S.A. — Especificación General del Sistema

## 1. Visión global

GameMetrics S.A. es una plataforma digital de análisis, descubrimiento y comercialización de videojuegos. Combina un catálogo analítico de aproximadamente 1.7 millones de títulos con un módulo de inteligencia de negocio (BI) que visualiza tendencias y KPIs en tiempo real mediante Big Data y streaming de eventos.

**Misión:** Centralizar el análisis de videojuegos y facilitar su descubrimiento y comercialización mediante Apache Pinot, Apache Kafka, FastAPI y Angular 17.

**Modelo de negocio:** B2C (usuarios finales) con proyección B2B (partners externos).

---

## 2. Actores globales del sistema

| Actor | Descripción |
|-------|-------------|
| Visitante | Navega la tienda y los dashboards sin autenticación. No puede usar wishlist ni comprar. |
| Usuario Registrado | Accede a wishlist, perfil y (futuro) carrito, biblioteca y reseñas. |
| Administrador | Gestiona colecciones empresariales (`emp_records`) y usuarios. |
| Administrador ETL | Ejecuta el pipeline Parquet→Pinot y recargas Kafka. |
| Analista BI | Consulta dashboards KPI y reportes analíticos. |
| Sistema (Kafka producer) | Emite eventos en cada operación transaccional; garantiza upsert idempotente. |
| Partner externo (futuro) | Consume endpoints documentados con OpenAPI. |

---

## 3. Resumen de niveles, departamentos y paquetes

| Nivel | Código | Departamento | Paquete | Estado |
|-------|--------|--------------|---------|--------|
| Estratégico | 001 | Gerencia General | BI / Analítica | Implementado |
| Táctico | 002 | Administración de Plataforma | empresa | Implementado |
| Táctico | 002 | Administración de Plataforma | dimensiones | Implementado |
| Táctico | 002 | Administración de Plataforma | etl | Implementado |
| Táctico | 002 | Ventas / Marketing | ventas | Implementado |
| Táctico | 002 | Analytics BI | analytics-bi | Implementado |
| Operativo | 003 | Cuentas y Acceso | auth | Implementado |
| Operativo | 003 | Tienda | tienda (store) | Implementado |
| Operativo | 003 | Tienda | wishlist | Implementado |
| Operativo | 003 | Comercio | carrito | Planificado |
| Operativo | 003 | Comercio | biblioteca | Planificado |
| Operativo | 003 | Comercio | resenas | Planificado |

---

## 4. Arquitectura de alto nivel

```
Visitante / Usuario Registrado / Administrador
        │
        ▼
Angular 17 (SPA — nginx:80)
        │ HTTP / REST
        ▼
FastAPI (Python 3.11 — puerto 8000)
  ├── /auth     → auth.router
  ├── /store    → store.router
  ├── /user     → user.router
  ├── /empresa  → empresa.router
  ├── /api/dashboard → dashboard.router
  ├── /dimensiones   → dimensiones.router
  └── /games         → games.router (legacy)
        │
        ├── Lectura: Apache Pinot (broker:8099)
        │     ├── OFFLINE: fact_videogames + 5 dimensiones
        │     └── REALTIME: fact_users, fact_wishlist, emp_records
        │
        └── Escritura: Apache Kafka (kafka:9092)
              topic: fact_users, fact_wishlist, emp_records
              (futuros: purchases, reviews)

ETL (Flask — etl_server.py:5001)
  └── Scripts 00..09 → Parquet → Pinot OFFLINE

RAWG API (externa) — imágenes, screenshots, descripciones
```

---

## 5. Principios de arquitectura (P1-P6)

| Código | Principio |
|--------|-----------|
| P1 | Toda escritura transaccional pasa por Kafka → Pinot. Nunca escritura directa a Pinot. |
| P2 | Una sola fuente de verdad por tabla; borrado lógico (tombstone `deleted=TRUE`). |
| P3 | PocketBase está ELIMINADO. Todo flujo de datos usa Kafka → Pinot. |
| P4 | Consistencia eventual < 2 segundos entre evento Kafka y visibilidad en Pinot REALTIME. |
| P5 | Secretos (RAWG, JWT_SECRET) solo en backend vía variables de entorno. |
| P6 | Catálogo analítico OFFLINE inmutable por semana; filtrado con `semana <= N` (1-17). |

---

## 6. Objetivos estratégicos (OE)

| Código | Objetivo |
|--------|----------|
| OE1 | Proveer un catálogo de videojuegos con datos enriquecidos y análisis de tendencias. |
| OE2 | Ofrecer una experiencia de tienda en línea segura y funcional para usuarios B2C. |
| OE3 | Centralizar la gestión empresarial (empleados, contratos, campañas) en una sola plataforma. |
| OE4 | Escalar el análisis a millones de registros con latencia sub-segundo mediante Apache Pinot. |

---

## 7. Reglas generales del sistema

| Código | Regla |
|--------|-------|
| RG-001 | Contraseñas siempre con bcrypt; nunca en texto plano ni en logs. |
| RG-002 | Endpoints protegidos validan JWT Bearer antes de operar. |
| RG-003 | Toda entrada de texto en queries Pinot pasa por `_esc()` (prevención de inyección SQL). |
| RG-004 | Precio calculado como `max(1.99, rating*8 + metacritic*0.4)`; si ambos son 0 → 0.00 (gratis). |
| RG-005 | Los módulos del backend son independientes; cada uno tiene `router.py` + archivos por responsabilidad. |
| RG-006 | El frontend usa un servicio Angular por dominio; componentes standalone; rutas protegidas con `authGuard`. |

---

## 8. Requisitos no funcionales globales

| Código | Requisito |
|--------|-----------|
| RNF-SYS-001 | Los dashboards KPI DEBEN responder en menos de 2 segundos sobre 1.7 M de registros. |
| RNF-SYS-002 | Los gráficos analíticos DEBEN responder en menos de 3 segundos. |
| RNF-SYS-003 | La consistencia eventual entre Kafka y Pinot REALTIME DEBE ser < 2 segundos. |
| RNF-SYS-004 | El sistema DEBE correr completamente en Docker Compose (red `172.20.0.0/16`). |
| RNF-SYS-005 | JWT tokens DEBEN expirar en 7 días (HS256). |
