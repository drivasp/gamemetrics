# GameMetrics S.A.

Plataforma digital de **análisis, descubrimiento y comercialización de videojuegos**. Combina un catálogo de ~1,7 millones de títulos con inteligencia de negocio en tiempo real, tienda digital y módulos de comercio extendidos (carrito, biblioteca, wallet, social y más), sobre una arquitectura orientada a eventos con **Apache Pinot** y **Apache Kafka**.

> Proyecto académico — Construcción de Software (UTQ) · Autor: Dayver Yhair Rivas Piloso

## Contexto del proyecto

GameMetrics S.A. nació como plataforma B2C con proyección B2B para el mercado latinoamericano. La documentación estratégica original (Balanced Scorecard, casos de uso CU-O01…CU-O13) describe cuatro objetivos estratégicos:

| Código | Objetivo |
|--------|----------|
| **OE1** | Penetración de mercado digital (registro automatizado, tienda, wishlist) |
| **OE2** | Escalabilidad comercial (APIs OpenAPI, integraciones, reseñas verificadas) |
| **OE3** | Infraestructura cloud contenerizada (Docker Compose, ETL, alta disponibilidad) |
| **OE4** | Inteligencia de negocio centralizada (modelo estrella, dashboard KPIs) |

### Evolución: de demo analítica a plataforma tipo Steam

El proyecto fue **refactorizado y ampliado** bajo la especificación `004-plataforma-pinot-steam`: evolucionar de una tienda básica + BI hacia una **plataforma de distribución digital completa**, manteniendo Pinot como única base de datos y Kafka como única vía de escritura transaccional.

| Fase | Alcance |
|------|---------|
| **Fase original** | Auth, tienda, wishlist, dashboard BI, empresa, dimensiones, ETL |
| **Fase comercio (Etapas 3–5)** | Carrito, checkout Stripe, biblioteca, reseñas verificadas |
| **Fase plataforma (004)** | Wallet, cupones, regalos, reembolsos, alertas, eventos, launcher, social, comunidad, partner B2B |

**Restricción arquitectónica:** no se usan PostgreSQL, MongoDB ni Redis. Toda persistencia vive en **Pinot OFFLINE + REALTIME**; toda escritura transaccional pasa por **Kafka** (principios P1–P6 en `openspec/config.yaml`).

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | Angular 21 (standalone), nginx |
| Backend | FastAPI (Python 3.12), 22 routers modulares |
| Datos analíticos | Apache Pinot 1.0.0 OFFLINE — `fact_videogames` + 5 dimensiones + catálogo comercial |
| Datos transaccionales | Apache Pinot REALTIME — usuarios, wishlist, comercio, social, etc. |
| Streaming | Apache Kafka 7.7.2 (aiokafka), upsert por clave + soft delete |
| ETL | Flask API + scripts numerados (`etl/00…16_*.py`) |
| API externa | RAWG API (media de juegos) |
| Pagos | Stripe (modo sandbox) |
| Auth | bcrypt + JWT HS256 (7 días) |
| Infra | Docker Compose, red `gamemetrics` 172.20.0.0/16 |

## Arquitectura

```
Angular SPA  ──HTTP──▶  FastAPI (22 routers)
                            │
              ┌─────────────┴─────────────┐
              │                           │
         kafka_send                  pinot_query
              │                           │
              ▼                           ▼
        Apache Kafka              Apache Pinot
        (topics REALTIME)    OFFLINE (Parquet) + REALTIME
```

**Principios clave:**

1. Toda escritura transaccional → Kafka → Pinot REALTIME (nunca escribir directo a Pinot).
2. Borrado lógico con tombstone (`deleted = TRUE`); no hay DELETE físico.
3. Consistencia eventual ≤ 2 s entre evento Kafka y visibilidad en Pinot.
4. Catálogo analítico filtrado con `WHERE semana <= N` (semanas 1–17).
5. PocketBase está **eliminado** del flujo activo (código legacy en `pocketbase/`).

## Módulos del backend

| Router | Prefijo / dominio | Estado |
|--------|-------------------|--------|
| `auth` | Registro, login, perfil, avatar | Implementado |
| `store` | Home, catálogo, detalle de juego | Implementado |
| `user` | Wishlist | Implementado |
| `cart` | Carrito de compras | Implementado |
| `checkout` | Pago Stripe sandbox | Implementado |
| `library` | Biblioteca de juegos comprados | Implementado |
| `reviews` | Reseñas verificadas | Implementado |
| `wallet` | Saldo y transacciones internas | Expansión 004 |
| `coupons` | Cupones y redenciones | Expansión 004 |
| `gifts` | Regalos entre usuarios | Expansión 004 |
| `refunds` | Devoluciones | Expansión 004 |
| `alerts` | Alertas de precio en wishlist | Expansión 004 |
| `events` | Eventos de comportamiento | Expansión 004 |
| `launcher` | Instalación y descargas | Expansión 004 |
| `social` | Amigos y actividad | Expansión 004 |
| `community` | Foros y moderación | Expansión 004 |
| `dashboard` | KPIs y gráficas BI | Implementado |
| `games` | Listado analítico de juegos | Implementado |
| `dimensiones` | Tablas de dimensión (solo lectura) | Implementado |
| `empresa` | CRUD 10 colecciones empresariales | Implementado |

Documentación detallada por paquete: `specs/` (niveles estratégico, táctico, operativo y plataforma 004).

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con Docker Compose v2)
- Windows PowerShell 5+ (para `inicio.ps1`)
- ~8 GB RAM libres recomendados (Pinot + Kafka + Zookeeper)
- Claves opcionales: [RAWG API](https://rawg.io/apidocs), [Stripe sandbox](https://stripe.com/docs/keys)

## Configuración

1. Copia las variables de entorno:

```powershell
Copy-Item backend\.env.example backend\.env
```

2. Edita `backend\.env` con tus claves:

```env
PINOT_BROKER_URL=http://localhost:8099
PINOT_CONTROLLER_URL=http://localhost:9000
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
RAWG_API_KEY=tu_clave_rawg
JWT_SECRET=genera_un_secreto_largo_y_aleatorio
FRONTEND_URL=http://localhost:4200
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

3. Coloca el dataset Parquet en `etl/data/stage/videogames.parquet` (o carga semanas desde el panel ETL del dashboard).

## Arranque rápido

Desde la raíz del proyecto:

```powershell
.\inicio.ps1
```

El script:

1. Limpia ZooKeeper/Kafka (evita `NodeExistsException`).
2. Levanta los 8 servicios Docker Compose.
3. Ejecuta bootstrap de tablas REALTIME de comercio (fases 04–06).
4. Aplica bootstraps de fases 2–5 si aún no se han ejecutado.

**Servicios disponibles:**

| Servicio | URL |
|----------|-----|
| Frontend (Angular) | http://localhost:4200 |
| Backend API + Swagger | http://localhost:8080/docs |
| Pinot Controller | http://localhost:9000 |
| Pinot Broker | http://localhost:8099 |
| Kafka | localhost:9092 |

### Bootstrap destructivo (recrear tablas comercio)

```powershell
.\inicio.ps1 -BootstrapCommerce
```

> Borra y recrea tablas REALTIME de comercio. Carrito, biblioteca y reseñas pueden perderse hasta que Kafka reindexe.

## Estructura del repositorio

```
.
├── backend/           # FastAPI — routers por dominio
├── frontend/
│   └── videogames-dashboard/   # Angular SPA
├── etl/               # Pipeline Parquet → Pinot + schemas
├── docker/            # Configuraciones auxiliares Docker
├── specs/             # Especificaciones OpenSpec por nivel
├── openspec/          # Constitución y reglas del proyecto
├── sql/               # Consultas SQL de referencia
├── utils/             # Utilidades auxiliares
├── docker-compose.yml
└── inicio.ps1         # Script de arranque completo
```

## Panel ETL (Dashboard)

Desde el dashboard en `/` puedes ejecutar jobs del pipeline:

- Cargar semanas Parquet → Pinot OFFLINE
- Recargar colecciones empresa vía Kafka
- Regenerar dimensiones
- Bootstrap de catálogo comercial, promociones y cupones

## Demo en video

[GameMetrics S.A. — Demostración del sistema](https://youtu.be/ev7dWV0j5-Y)

## Roadmap pendiente

- [ ] Completar las 50 tablas Pinot de la spec 004
- [ ] Documentación OpenAPI al 100 % en `/docs`
- [ ] CI/CD con GitHub Actions
- [ ] Migración a Kubernetes + CDN
- [ ] Modelos ML (segmentación, abandono wishlist, recomendaciones)

## Licencia

Proyecto académico — uso educativo. Consultar con el autor antes de redistribución comercial.
