# Documento de Especificaciones — Casos de Uso Operativos

**GameMetrics S.A.** — Plataforma de Análisis y Tienda de Videojuegos  
**Formato:** Referencia GA07 (UTQ · Construcción de Software)  
**Autor:** Rivas Piloso Dayver Yhair  
**Repositorio:** https://github.com/drivasp/gamemetrics

---

## Tabla de contenidos

1. [Constitución del proyecto](#1-constitución-del-proyecto)
2. [Paquete auth](#2-paquete-auth--autenticación)
3. [Paquete tienda](#3-paquete-tienda--tienda-de-videojuegos)
4. [Paquete wishlist](#4-paquete-wishlist--lista-de-deseos)
5. [Paquete carrito](#5-paquete-carrito--carrito-de-compras)
6. [Paquete checkout](#6-paquete-checkout--pago-y-órdenes)
7. [Paquete biblioteca](#7-paquete-biblioteca--juegos-comprados)
8. [Paquete resenas](#8-paquete-resenas--reseñas-verificadas)
9. [Paquete wallet](#9-paquete-wallet--cartera-interna)
10. [Paquete refunds](#10-paquete-refunds--reembolsos)
11. [Paquete gifts](#11-paquete-gifts--regalos)
12. [Paquete launcher](#12-paquete-launcher--instalación-y-juego)
13. [Paquete social](#13-paquete-social--amigos-y-actividad)
14. [Paquete alerts](#14-paquete-alerts--alertas-y-notificaciones)
15. [Paquete coupons](#15-paquete-coupons--cupones)
16. [Paquete community](#16-paquete-community--comunidad-y-b2b)
17. [Paquetes tácticos: etl, dimensiones, empresa](#17-paquetes-tácticos)

---

## 1. Constitución del proyecto

### 1.1 Visión

Convertirse en la plataforma de referencia en análisis y comercialización digital de videojuegos en Latinoamérica.

### 1.2 Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI (Python 3.12), routers modulares |
| Datos | Apache Pinot OFFLINE + REALTIME |
| Streaming | Apache Kafka (aiokafka) |
| Frontend | Angular 21, nginx |
| Auth | bcrypt + JWT HS256 (7 días) |
| ETL | Flask API + scripts `etl/00…16` |

### 1.3 Principios (P1–P6)

- P1: Escrituras transaccionales solo vía Kafka → Pinot.
- P2: Upsert por PK; soft delete con `deleted = TRUE`.
- P3: PocketBase eliminado del flujo activo.
- P4: Consistencia eventual ≤ 2 segundos.
- P5: Secretos solo en backend (`.env`).
- P6: Catálogo OFFLINE filtrado con `semana <= N`.

---

## 2. Paquete auth — Autenticación

**Estado:** Implementado  
**Ubicación backend:** `backend/auth/`  
**Tabla Pinot:** `fact_users` (REALTIME)

### Objetivo

Gestionar registro, login, perfil y avatar. Toda escritura pasa por Kafka topic `fact_users`.

### Actores

| Actor | Rol |
|-------|-----|
| Visitante | Registro y login |
| Usuario Registrado | Perfil y avatar |
| Sistema Kafka | Persistencia upsert |

### Casos de uso

| Código | Nombre | Actor |
|--------|--------|-------|
| CU-O01 | Registrar usuario | Visitante |
| CU-O02 | Iniciar sesión | Visitante |
| CU-O08 | Editar perfil y avatar | Usuario |

### Historias de usuario

- **US-AUTH-001:** Como visitante, quiero registrarme con email y contraseña para acceder a funciones exclusivas.
- **US-AUTH-002:** Como visitante, quiero iniciar sesión y obtener JWT por 7 días.
- **US-AUTH-004:** Como usuario, quiero editar nombre y bio en `/profile`.

### Requisitos funcionales (selección)

| Código | Requisito |
|--------|-----------|
| RF-AUTH-001 | `POST /auth/register` → `{token, user}` |
| RF-AUTH-004 | `POST /auth/login` con bcrypt |
| RF-AUTH-006 | `GET /auth/profile` con JWT Bearer |
| RF-AUTH-007 | `PUT /auth/profile` vía Kafka upsert |
| RF-AUTH-008 | `POST /auth/avatar` multipart → `/static/avatars/` |

### Reglas de negocio

- RN-AUTH-001: Email único en `fact_users` con `deleted = FALSE`.
- RN-AUTH-002: Borrado lógico (tombstone), nunca DELETE físico.

### Entradas y salidas

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| POST /auth/register | email, password, display_name? | token, UserDTO |
| POST /auth/login | email, password | token, UserDTO |
| GET /auth/profile | Bearer JWT | UserDTO |

### Escenario Gherkin — Registro exitoso

```gherkin
Dado que el visitante envía POST /auth/register con email nuevo
Cuando el backend hashea con bcrypt y emite kafka_send("fact_users", ...)
Entonces retorna HTTP 200 con token JWT
Y el usuario es visible en Pinot en menos de 2 segundos
```

### Criterios de aceptación

- CA-AUTH-001: Email duplicado → HTTP 400.
- CA-AUTH-003: Login correcto → JWT válido 7 días.
- CA-AUTH-005: Perfil sin token → HTTP 401.

### Navegación UI (video)

`http://localhost:4200/store` → **Iniciar sesión** → pestaña **Registrarse** → completar formulario.

### Dependencias

`shared/kafka_producer.py`, `shared/cliente_pinot.py`, paquetes `wishlist`, `carrito` (requieren JWT).

---

## 3. Paquete tienda — Tienda de videojuegos

**Estado:** Implementado  
**Ubicación:** `backend/tienda/`  
**Tablas:** `fact_videogames`, `dim_*`, `fact_game_products` (OFFLINE)

### Objetivo

Home, catálogo con filtros, detalle enriquecido con RAWG o placeholder SVG.

### Casos de uso

| Código | Nombre | Actor | Ruta |
|--------|--------|-------|------|
| CU-O03 | Ver home tienda | Visitante | `/store` |
| CU-O04 | Filtrar catálogo | Visitante | `/store/catalog` |
| CU-O05 | Ver detalle juego | Visitante | `/store/game/:slug` |

### Reglas de negocio

- RN-TIENDA-001: Precio = `max(1.99, rating×8 + metacritic×0.4)`; si ambos 0 → gratis.
- RN-TIENDA-002: Filtro semana acumulado `semana <= N`.

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /store/featured | Destacados |
| GET | /store/new-releases | Nuevos lanzamientos |
| GET | /store/games | Catálogo paginado + filtros |
| GET | /store/games/{slug} | Detalle + similares |

### Escenario Gherkin — Catálogo con filtros

```gherkin
Dado que el visitante abre /store/catalog
Cuando filtra por género "Action" y busca "Half"
Entonces ve grid paginado con contador total
Y cada juego muestra precio e imagen (RAWG o placeholder)
```

### Navegación UI (video)

`/store` → secciones Destacados / Nuevos → **CATÁLOGO** → buscador y filtros → clic en juego.

---

## 4. Paquete wishlist — Lista de deseos

**Estado:** Implementado  
**Ubicación:** `backend/wishlist/`  
**Tabla:** `fact_wishlist`

### Objetivo

Agregar, listar y eliminar juegos deseados. PK compuesta `{user_id}_{game_slug}`.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O06 | Agregar a wishlist |
| CU-O07 | Ver y eliminar de wishlist |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /user/wishlist |
| GET | /user/wishlist |
| GET | /user/wishlist/check/{slug} |
| DELETE | /user/wishlist/{slug} |

### Reglas

- RN-WISH-001: No duplicar mismo juego (HTTP 409).
- RN-WISH-003: Eliminación por tombstone Kafka.

### Navegación UI (video)

Login → ficha juego → **Agregar a Wishlist** → `/profile` → lista de deseados.

---

## 5. Paquete carrito — Carrito de compras

**Estado:** Implementado  
**Ubicación:** `backend/carrito/`  
**Tabla:** `fact_cart`

### Objetivo

Agregar juegos, ver total, vaciar carrito antes del checkout.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O09a | Agregar ítem al carrito |
| CU-O09b | Ver y vaciar carrito |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /cart/items |
| GET | /cart |
| DELETE | /cart/items/{slug} |
| DELETE | /cart |

### Navegación UI (video)

Ficha juego → **Añadir al carro** → popup con contador → navbar **Carrito** → `/my-cart`.

---

## 6. Paquete checkout — Pago y órdenes

**Estado:** Implementado  
**Ubicación:** `backend/checkout/`  
**Tablas:** `fact_orders`, `fact_order_items`, `fact_payments`, `fact_purchases`

### Objetivo

Procesar pago sandbox o con cartera; generar compras en biblioteca.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O09c | Checkout pago sandbox |
| CU-O12 | Checkout con cartera |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /checkout/sandbox |
| POST | /checkout/wallet |

### Escenario Gherkin — Compra sandbox

```gherkin
Dado un carrito con 1 juego y usuario autenticado
Cuando completa POST /checkout/sandbox en /payment
Entonces se crean registros en fact_orders y fact_purchases
Y el carrito queda vacío
Y el juego aparece en /my-library
```

### Navegación UI (video)

`/my-cart` → **Continuar al pago** → `/payment` → **Pago inmediato (sandbox)** → éxito → biblioteca.

---

## 7. Paquete biblioteca — Juegos comprados

**Estado:** Implementado  
**Ubicación:** `backend/biblioteca/`  
**Tabla:** `fact_purchases` (solo lectura)

### Objetivo

Listar juegos adquiridos; validar posesión para reseñas y regalos.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O10 | Ver biblioteca |
| CU-O10b | Verificar posesión (interno) |

### Endpoints

| Método | Ruta |
|--------|------|
| GET | /library |
| GET | /library/check/{slug} |

### Reglas

- RN-LIB-001: Biblioteca inmutable para el usuario (sin DELETE).
- RN-LIB-003: Fuente de verdad = `fact_purchases`.

### Navegación UI (video)

Navbar → **BIBLIOTECA** → `/my-library`.

---

## 8. Paquete resenas — Reseñas verificadas

**Estado:** Implementado  
**Ubicación:** `backend/resenas/`  
**Tabla:** `fact_reviews`

### Objetivo

Solo compradores pueden reseñar (validación contra `fact_purchases`).

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O13 | Crear reseña verificada |
| CU-O13b | Leer reseñas públicas |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /reviews/{slug} |
| GET | /reviews/{slug} |
| PUT | /reviews/{slug} |
| DELETE | /reviews/{slug} |

### Reglas

- RN-REV-001: Solo si `GET /library/check/{slug}` → owned=true.
- RN-REV-002: Una reseña activa por usuario y juego.

### Navegación UI (video)

Tras compra → ficha del juego → formulario estrellas + comentario.

---

## 9. Paquete wallet — Cartera interna

**Estado:** Implementado  
**Ubicación:** `backend/wallet/`  
**Tablas:** `fact_user_wallets`, `fact_wallet_transactions`

### Objetivo

Recargar saldo simulado y pagar compras/regalos.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O11 | Recargar cartera |
| CU-O12 | Pagar con cartera (con checkout) |

### Endpoints

| Método | Ruta |
|--------|------|
| GET | /wallet |
| POST | /wallet/deposit |
| GET | /wallet/transactions |

### Navegación UI (video)

Navbar icono **$** → `/my-wallet` → **Añadir fondos**.

---

## 10. Paquete refunds — Reembolsos

**Estado:** Implementado  
**Ubicación:** `backend/refunds/`  
**Tabla:** `fact_refunds`

### Objetivo

Devolución dentro de 14 días; acredita saldo a cartera.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O17 | Solicitar reembolso |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /refunds |
| GET | /refunds |

### Navegación UI (video)

`/my-library` → menú juego → **Solicitar reembolso** → wizard 3 pasos.

---

## 11. Paquete gifts — Regalos

**Estado:** Implementado  
**Ubicación:** `backend/gifts/`  
**Tabla:** `fact_gifts`

### Objetivo

Enviar juego a otro usuario pagando con cartera.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O15 | Regalar juego |
| CU-O15b | Aceptar/rechazar regalo |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /gifts |
| GET | /gifts/received |
| POST | /gifts/{id}/accept |
| POST | /gifts/{id}/reject |

### Navegación UI (video)

Ficha → **Regalar a un amigo** → destinatario en `/my-gifts` → **Aceptar**.

---

## 12. Paquete launcher — Instalación y juego

**Estado:** Implementado  
**Ubicación:** `backend/launcher/`  
**Tablas:** `fact_install_states`, `fact_play_sessions`, `fact_builds`, `fact_achievements`

### Objetivo

Simular instalación, descarga, sesión de juego y logros.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O14 | Instalar juego |
| CU-O14b | Jugar / detener sesión |
| CU-O14c | Desinstalar |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /launcher/install |
| GET | /launcher/progress/{slug} |
| POST | /launcher/play/start |
| POST | /launcher/play/stop |
| POST | /launcher/uninstall |

### Navegación UI (video)

`/my-library` → **Instalar** → barra progreso → **Jugar** → overlay → **Detener**.

---

## 13. Paquete social — Amigos y actividad

**Estado:** Implementado  
**Ubicación:** `backend/social/`  
**Tablas:** `fact_friendships`, `fact_notifications`, `fact_user_activity`

### Objetivo

Solicitudes de amistad, lista de amigos, feed de actividad.

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O16a | Enviar/aceptar solicitud amistad |
| CU-O16b | Ver lista de amigos |

### Endpoints

| Método | Ruta |
|--------|------|
| GET | /social/friends |
| POST | /social/friends/request |
| POST | /social/friends/accept/{id} |

### Navegación UI (video)

Navbar **AMIGOS** → `/my-friends` → buscar por email → solicitar.

---

## 14. Paquete alerts — Alertas y notificaciones

**Estado:** Implementado  
**Ubicación:** `backend/alerts/`  
**Tablas:** `fact_wishlist_price_alerts`, `fact_notifications`

### Objetivo

Dropdown de notificaciones en navbar; alertas de precio en wishlist (roadmap UI completa).

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O16c | Ver notificaciones |
| CU-O18 | Alerta baja de precio (roadmap) |

### Endpoints

| Método | Ruta |
|--------|------|
| GET | /alerts |
| POST | /alerts/price |

### Navegación UI (video)

Navbar → icono **notifications** → dropdown alertas.

---

## 15. Paquete coupons — Cupones

**Estado:** Parcial  
**Ubicación:** `backend/coupons/`  
**Tablas:** `fact_coupons`, `fact_coupon_redemptions`, `fact_promotions`

### Objetivo

Aplicar cupones en checkout (semilla vía ETL `seed-promociones`).

### Casos de uso

| Código | Nombre |
|--------|--------|
| CU-O19 | Aplicar cupón en checkout |

### Endpoints

| Método | Ruta |
|--------|------|
| POST | /coupons/validate |
| POST | /coupons/redeem |

---

## 16. Paquete community — Comunidad y B2B

**Estado:** Parcial (API activa, UI en `/my-partner`, `/my-family`)  
**Ubicación:** `backend/community/`  
**Tablas:** foros, family, partners, api_keys, search_queries

### Objetivo

Foros por juego, family sharing, portal partner B2B.

### Casos de uso (roadmap UI)

| Código | Nombre |
|--------|--------|
| CU-O20 | Publicar en foro del juego |
| CU-O21 | Compartir biblioteca familiar |
| CU-O22 | Gestionar catálogo partner |

---

## 17. Paquetes tácticos

### 17.1 Paquete etl

**Ubicación:** `etl/`  
**Actor:** Administrador ETL

| Código | Caso de uso |
|--------|-------------|
| CU-T01 | Cargar semana Parquet → `fact_videogames` |
| CU-T01b | Crear tablas REALTIME (40) |
| CU-T01c | Cargar catálogo comercial OFFLINE |
| CU-T01d | Seed promociones y cupones |

**UI:** `http://localhost:4200/` Panel ETL.

### 17.2 Paquete dimensiones

**Ubicación:** `backend/dimensiones/`  
**Tablas:** `dim_generos`, `dim_plataformas`, `dim_desarrolladores`, `dim_publicadores`, `dim_esrb`

| Código | Caso de uso |
|--------|-------------|
| CU-T02 | Consultar dimensiones post-ETL (solo lectura) |

**UI:** `/dimensiones`

### 17.3 Paquete empresa

**Ubicación:** `backend/empresa/`  
**Tabla:** `emp_records` (10 colecciones)

| Código | Caso de uso |
|--------|-------------|
| CU-T03 | CRUD registro empresarial vía Kafka |

**UI:** `/empresa`

---

## Anexo A — Matriz paquete ↔ caso de uso ↔ tabla

| Paquete | CU principal | Tabla Pinot |
|---------|--------------|-------------|
| auth | CU-O01, CU-O02, CU-O08 | fact_users |
| tienda | CU-O03–CU-O05 | fact_videogames |
| wishlist | CU-O06, CU-O07 | fact_wishlist |
| carrito | CU-O09a | fact_cart |
| checkout | CU-O09c, CU-O12 | fact_orders, fact_payments, fact_purchases |
| biblioteca | CU-O10 | fact_purchases |
| resenas | CU-O13 | fact_reviews |
| wallet | CU-O11 | fact_user_wallets |
| refunds | CU-O17 | fact_refunds |
| gifts | CU-O15 | fact_gifts |
| launcher | CU-O14 | fact_install_states |
| social | CU-O16a | fact_friendships |
| alerts | CU-O16c | fact_notifications |
| etl | CU-T01 | OFFLINE + REALTIME |
| empresa | CU-T03 | emp_records |

---

## Anexo B — Referencia cruzada GA07 / TA06

Los códigos CU-O01…CU-O17 del documento estratégico TA06 se mantienen y extienden con casos de plataforma (wallet, launcher, gifts, social) documentados en `specs/004-plataforma-pinot-steam/`.

Para historias paso a paso del video, ver `docs/CASOS_DE_USO.md`.
