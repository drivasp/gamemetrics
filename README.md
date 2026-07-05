# GameMetrics S.A.

Plataforma digital de **análisis, descubrimiento y comercialización de videojuegos**. Combina un catálogo de ~1,7 millones de títulos con inteligencia de negocio en tiempo real, **tienda estilo Steam**, comercio completo (carrito → pago → biblioteca), launcher simulado, regalos, social y más — todo sobre **Apache Pinot** + **Apache Kafka**.

> Proyecto académico — Construcción de Software (UTQ) · Autor: Dayver Yhair Rivas Piloso

**Estado actual:** demo operativa end-to-end en Docker. Frontend Angular con UI Steam, 18 routers FastAPI activos, flujos de compra/reembolso/regalo/launcher verificados, suite E2E Playwright (20 tests).

| Demo | URL |
|------|-----|
| **App (ETL + Tienda)** | http://localhost:4000 |
| **Tienda directa** | http://localhost:4000/store |
| **API + Swagger** | http://localhost:8080/docs |

---

## Qué hay implementado en esta etapa

### Tienda y descubrimiento (`tienda`)

- Home con **carrusel spotlight** (trailers al hover), secciones **Nuevos lanzamientos**, **Más populares** y **Gratis para jugar**.
- Catálogo paginado con búsqueda, filtros por género y juegos gratis.
- Ficha de juego: precio, descuentos, similares, foro comunitario, reseñas verificadas.
- **Portadas unificadas:** componente `GameCoverComponent` con cadena URL → placeholder SVG del backend → fallback inline GameMetrics.
- Integración opcional **RAWG** para imágenes reales (`RAWG_API_KEY`).

### Cuenta y perfil (`auth`, `wishlist`)

- Registro / login JWT (7 días), modal de auth en la tienda.
- Perfil con avatar, email y **lista de deseos** (tab **LISTA DE DESEOS** en navbar).
- Wishlist persistente en Pinot REALTIME (`fact_wishlist`).

### Comercio completo (`carrito`, `checkout`, `wallet`, `coupons`, `refunds`)

| Flujo | Ruta UI | Descripción |
|-------|---------|-------------|
| Carrito | `/my-cart` | Añadir, quitar, popup con contador inmediato **Ver mi carro (N)** |
| Pago sandbox | `/payment` | Pago demo sin tarjeta + pago con **Cartera GameMetrics** |
| Éxito | `/payment/success` | Pantalla Steam con redirect automático a biblioteca |
| Cartera | `/my-wallet` | Recarga simulada ($5 / $20 / $50) e historial |
| Reembolso | `/my-library` | Wizard 3 pasos, política 14 días, saldo devuelto a cartera |
| Cupones | API `/coupons` | Redención en checkout (backend activo) |

> **Stripe:** opcional. La demo funciona al 100 % con **pago sandbox** y **cartera interna** sin configurar claves.

### Biblioteca y launcher (`biblioteca`, `launcher`)

- Biblioteca con grid de juegos comprados y portadas.
- **Instalar → descargar → Jugar** con overlay de sesión y cronómetro.
- Panel lateral: logros, tiempo jugado, desinstalar (conserva progreso).
- Reembolso integrado desde cada juego.

### Plataforma social y regalos (`gifts`, `social`, `alerts`, `community`, `events`)

| Módulo | Ruta UI | Qué hace |
|--------|---------|----------|
| Regalos | `/my-gifts` | Enviar desde ficha del juego, inbox/sent, aceptar/rechazar |
| Amigos | `/my-friends` | Solicitudes, aceptar, listado |
| Notificaciones | Navbar (campana) | Alertas de regalos, amigos, precios |
| Soporte / Partner / Family | `/my-support`, `/my-partner`, `/my-family` | Vistas conectadas a API social |
| Comunidad | Ficha del juego | Foro y posts (`/community`) |
| Eventos | Backend | Tracking de comportamiento (`/events`) |

### Reseñas (`resenas`)

- Reseñas **verificadas post-compra** en ficha del juego y biblioteca.
- Solo compradores pueden publicar; visibles para todos.

### Panel ETL / BI (`etl`, `dimensiones`, `empresa`)

- Dashboard en `/` con carga de semanas Parquet, dimensiones, tablas REALTIME y catálogo comercial.
- CRUD empresa y consulta de dimensiones (solo lectura).
- Módulo **dashboard BI analítico** (gráficas por género/plataforma/ESRB) archivado en `backend/_archivado/dashboard/` — reactivable si se necesita.

### Calidad y UX

- **Material Symbols Outlined** en toda la UI (sin emojis en botones).
- Tema visual **Steam** (`#1b2838`, `#66c0f4`, `#beee11`) en tienda, carrito, pago y biblioteca.
- **20 tests E2E** Playwright: registro, tienda, wishlist, carrito, compra, cartera, reembolso.
- Catálogo de historias de usuario: [`docs/CASOS_DE_USO.md`](docs/CASOS_DE_USO.md).

---

## Contexto del proyecto

GameMetrics S.A. nació como plataforma B2C con proyección B2B para el mercado latinoamericano. Cuatro objetivos estratégicos (Balanced Scorecard):

| Código | Objetivo |
|--------|----------|
| **OE1** | Penetración de mercado digital (registro, tienda, wishlist) |
| **OE2** | Escalabilidad comercial (APIs OpenAPI, reseñas verificadas, regalos) |
| **OE3** | Infraestructura cloud contenerizada (Docker Compose, ETL, HA) |
| **OE4** | Inteligencia de negocio centralizada (modelo estrella, KPIs) |

### Evolución por fases

| Fase | Alcance | Estado |
|------|---------|--------|
| **Original** | Auth, tienda, wishlist, empresa, dimensiones, ETL | ✅ Operativo |
| **Comercio** | Carrito, checkout, biblioteca, reseñas, wallet, reembolsos | ✅ Operativo |
| **Plataforma 004** | Regalos, launcher, social, alertas, comunidad, eventos | ✅ Operativo (demo) |
| **BI analítico** | Dashboard KPIs por dimensión | 📦 Archivado (`_archivado`) |

**Restricción arquitectónica:** no hay PostgreSQL, MongoDB ni Redis. Toda persistencia en **Pinot OFFLINE + REALTIME**; toda escritura transaccional vía **Kafka** (P1–P6 en `openspec/config.yaml`).

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | Angular 21 (standalone), nginx, Material Symbols |
| Backend | FastAPI (Python 3.12), **18 routers** modulares |
| Datos analíticos | Apache Pinot 1.0.0 OFFLINE — `fact_videogames` + dimensiones + catálogo |
| Datos transaccionales | Apache Pinot REALTIME — usuarios, comercio, social, launcher… |
| Streaming | Apache Kafka 7.7.2 (aiokafka), upsert + soft delete |
| ETL | Flask API + scripts (`etl/00…16_*.py`) |
| Media | RAWG API (opcional) + placeholders SVG propios |
| Pagos | Sandbox interno + Stripe opcional |
| Auth | bcrypt + JWT HS256 (7 días) |
| Tests | Playwright (`e2e/`) |
| Infra | Docker Compose, red `gamemetrics` 172.20.0.0/16 |

---

## Arquitectura

```
Angular SPA (:4000)  ──HTTP──▶  FastAPI (:8080) — 18 routers
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
               kafka_send                         pinot_query
                    │                                   │
                    ▼                                   ▼
              Apache Kafka                      Apache Pinot
              (topics REALTIME)          OFFLINE (Parquet) + REALTIME
```

**Principios:**

1. Escritura transaccional → Kafka → Pinot REALTIME (nunca directo a Pinot).
2. Borrado lógico (`deleted = TRUE`); no DELETE físico.
3. Consistencia eventual ≤ ~2 s entre Kafka y consulta.
4. Catálogo filtrado por semana (`semana <= N`, semanas 1–17).
5. PocketBase **eliminado** del flujo activo.

---

## Routers API activos

Montados en `backend/main.py`:

```
/auth       /store      /user (wishlist)   /cart        /library
/reviews    /dimensiones /empresa          /wallet      /checkout
/coupons    /refunds    /gifts            /launcher    /social
/community  /events     /alerts
```

Swagger interactivo: http://localhost:8080/docs

Paquetes renombrados al español en código: `tienda`, `carrito`, `biblioteca`, `resenas`, `wishlist`. Copias legacy en inglés archivadas bajo `backend/_archivado/`.

---

## Rutas del frontend

| Ruta | Componente | Auth |
|------|------------|------|
| `/` | Panel ETL | No |
| `/store` | Home tienda | No |
| `/store/catalog` | Catálogo | No |
| `/store/game/:slug` | Ficha juego | No |
| `/profile` | Perfil + wishlist | Sí |
| `/my-cart` | Carrito | Sí |
| `/payment` | Checkout | Sí |
| `/payment/success` | Compra OK | Sí |
| `/my-library` | Biblioteca + launcher | Sí |
| `/my-wallet` | Cartera | Sí |
| `/my-gifts` | Regalos | Sí |
| `/my-friends` | Amigos | Sí |
| `/my-support` | Soporte | Sí |
| `/my-partner` | Partner B2B | Sí |
| `/my-family` | Family Sharing | Sí |
| `/empresa`, `/dimensiones` | Admin | No |

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Compose v2
- Windows PowerShell 5+ (script `inicio.ps1`)
- ~8 GB RAM libres (Pinot + Kafka + Zookeeper)
- Node.js 20+ **solo** si corres E2E o `ng serve` local fuera de Docker

---

## Configuración

### Obligatorio (primera vez en máquina nueva)

```powershell
Copy-Item backend\.env.example backend\.env
```

El `.env` **no se commitea** (está en `.gitignore`). Cada desarrollador clona y copia el example.

Valores por defecto del example ya funcionan en Docker:

```env
PINOT_BROKER_URL=http://localhost:8099
PINOT_CONTROLLER_URL=http://localhost:9000
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
JWT_SECRET=cambia_este_secreto_en_produccion
FRONTEND_URL=http://localhost:4000
RAWG_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

| Variable | ¿Obligatoria? | Notas |
|----------|---------------|-------|
| `JWT_SECRET` | Recomendado cambiar | Cualquier string largo en local |
| `FRONTEND_URL` | Sí | Debe ser `http://localhost:4000` (puerto Docker) |
| `RAWG_API_KEY` | No | Sin clave → placeholders SVG con nombre del juego |
| `STRIPE_*` | No | Pago sandbox + cartera cubren la demo completa |
| `KAFKA_*`, `PINOT_*` | Sí (defaults OK) | Dentro de Docker usan hostnames del compose |

### Dataset Parquet

Coloca `etl/data/stage/videogames.parquet` **o** carga **Semana 1** desde el Panel ETL (`/` → **▶ Cargar Semana 1**). Sin datos, la tienda no muestra juegos.

---

## Arranque rápido

Desde la raíz del proyecto:

```powershell
.\inicio.ps1
```

El script:

1. Limpia estado ZooKeeper/Kafka (evita `NodeExistsException`).
2. Levanta los servicios Docker Compose.
3. Bootstrap de tablas REALTIME de comercio (si es primera vez).
4. Aplica bootstraps de fases 2–5 pendientes.

**Servicios:**

| Servicio | URL |
|----------|-----|
| Frontend (Angular + nginx) | http://localhost:4000 |
| Backend API | http://localhost:8080 |
| Swagger | http://localhost:8080/docs |
| Pinot Controller | http://localhost:9000 |
| Pinot Broker | http://localhost:8099 |
| Kafka | localhost:9092 |

### Recrear tablas comercio (destructivo)

```powershell
.\inicio.ps1 -BootstrapCommerce
```

> Borra tablas REALTIME de comercio. Carrito, biblioteca y compras se pierden hasta reindexar Kafka.

### Desarrollo frontend local (opcional)

```powershell
cd frontend/videogames-dashboard
npm ci
npm start   # :4200 con proxy a backend :8080
```

En Docker la app corre en **:4000** (nginx). El proxy dev incluye `/store/cover-placeholder`.

---

## Flujo demo recomendado (5 minutos)

1. **`.\inicio.ps1`** → esperar verde.
2. **`/`** → Cargar Semana 1 + Tablas REALTIME (si no lo hizo el script).
3. **`/store`** → explorar home, catálogo, ficha.
4. **Registrarse** → añadir al carrito → **Pago sandbox** → biblioteca.
5. **`/my-library`** → Instalar → Jugar.
6. (Opcional) Recargar cartera → regalar juego → aceptar en `/my-gifts`.
7. (Opcional) Reembolso desde biblioteca.

Historias detalladas paso a paso: [`docs/CASOS_DE_USO.md`](docs/CASOS_DE_USO.md).

---

## Tests automatizados (E2E)

Con Docker levantado (`localhost:4000` + `:8080`):

```powershell
cd e2e
npm ci
npm test
```

20 tests cubren: registro, login, tienda, catálogo, wishlist, carrito (contador popup), compra sandbox, cartera, reembolso y navegación dashboard ↔ tienda.

Variables opcionales:

```powershell
$env:E2E_BASE_URL = "http://localhost:4000"
$env:E2E_API_URL = "http://localhost:8080"
npm test
```

Reporte HTML: `npx playwright show-report` (desde `e2e/`).

---

## Portadas de juegos

| Modo | Comportamiento |
|------|----------------|
| **Sin RAWG** | SVG generado en backend: `GET /store/cover-placeholder/{slug}?title=...` |
| **Con RAWG** | Clave en `backend/.env` → búsqueda por slug/nombre, fallback a SVG |

Tras cambiar `.env`:

```powershell
docker compose build backend
docker compose up -d backend
```

Componente frontend: `frontend/videogames-dashboard/src/app/shared/game-cover/`.

---

## Estructura del repositorio

```
.
├── backend/              # FastAPI — routers por dominio (+ _archivado/)
├── frontend/
│   └── videogames-dashboard/   # Angular SPA + shared/game-cover
├── etl/                  # Pipeline Parquet → Pinot
├── e2e/                  # Playwright — tests operativos
├── docs/
│   └── CASOS_DE_USO.md   # Historias de usuario completas
├── specs/                # OpenSpec por nivel
├── openspec/             # Constitución del proyecto
├── docker-compose.yml
├── inicio.ps1            # Arranque completo
└── README.md
```

---

## Panel ETL (Dashboard)

Desde `/`:

- Cargar semanas Parquet → Pinot OFFLINE
- Dimensiones (géneros, plataformas, publishers)
- Tablas REALTIME (`fact_users`, `fact_cart`, `fact_orders`, …)
- Bootstrap catálogo comercial, promociones y cupones
- Recarga empresa vía Kafka

---

## Demo en video

[GameMetrics S.A. — Demostración del sistema](https://youtu.be/ev7dWV0j5-Y)

*(Grabación anterior; la UI actual incluye mejoras Steam posteriores.)*

---

## Roadmap

- [x] Tienda estilo Steam con portadas y Material Icons
- [x] Comercio sandbox + cartera + reembolsos
- [x] Biblioteca con launcher simulado
- [x] Regalos, amigos, alertas (API + UI)
- [x] Suite E2E Playwright
- [x] Documentación de casos de uso
- [ ] Completar las 50 tablas Pinot de la spec 004
- [ ] Reactivar dashboard BI analítico desde `_archivado`
- [ ] CI/CD con GitHub Actions
- [ ] Migración a Kubernetes + CDN
- [ ] Modelos ML (recomendaciones, abandono wishlist)

---

## Licencia

Proyecto académico — uso educativo. Consultar con el autor antes de redistribución comercial.
