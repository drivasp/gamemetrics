# Casos de uso — GameMetrics S.A.

Historias de usuario completas, paso a paso. Prioridad: **calidad y flujo real**, no cantidad de filas en una tabla.

**Demo:** `http://localhost:4000` (dashboard + ETL) · `http://localhost:4000/store` (tienda)

---

## Cómo leer este documento

Cada historia indica:

- **Nivel:** Estratégico · Táctico · Operativo  
- **Paquete(s):** módulo backend / área funcional  
- **Precondiciones:** qué debe estar listo antes  
- **Pasos:** qué hace el actor en la UI  
- **Resultado esperado:** qué debe ver o recibir  

---

## Nivel táctico — Preparar el escenario (datos)

### HU-T-ETL-001 · El analista carga la semana 1 para abrir la tienda

| | |
|---|---|
| **Nivel** | Táctico |
| **Paquetes** | `etl`, `empresa`, `dimensiones` |
| **Actor** | Administrador ETL |

**Precondiciones:** Docker levantado (`docker compose up -d`). Pinot y Kafka en verde.

**Pasos:**

1. Abro `http://localhost:4000/` — veo el **Panel ETL** con pestañas Dataset, Dimensiones, Tablas REALTIME, etc.
2. En **Dataset Principal**, selecciono **Semana 1** y pulso **▶ Cargar Semana 1**. Espero a que el estado pase a completado.
3. Ejecuto **Dimensiones** (script 09) para géneros, plataformas, publishers.
4. Ejecuto **Tablas REALTIME** para crear `fact_users`, `fact_cart`, `fact_wishlist`, `fact_user_wallets`, `fact_orders`, `fact_payments`, `fact_purchases`, `fact_refunds`, etc.
5. (Opcional) Cargo **Empresa** si voy a usar CRUD administrativo.

**Resultado esperado:** `GET http://localhost:8080/store/featured` devuelve juegos. La tienda en `/store` muestra destacados con portadas (placeholder SVG o RAWG si hay API key).

---

## Nivel operativo — Tienda y descubrimiento

### HU-O-TIENDA-001 · La visitante Ana descubre un juego desde la home

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `tienda` |
| **Actor** | Visitante (sin cuenta) |
| **CUs relacionados** | CU-O06, CU-O08 |

**Precondiciones:** Semana 1+ cargada en Pinot (HU-T-ETL-001).

**Pasos:**

1. Entro a `http://localhost:4000/store`.
2. Recorro el carrusel y la sección **Destacados y recomendados** — cada tarjeta muestra nombre, precio y **portada** (SVG con nombre del juego o imagen RAWG).
3. Hago clic en un juego → llego a `/store/game/{slug}`.
4. Leo ficha, precio, géneros y juegos similares.

**Resultado esperado:** Detalle carga sin error 404. No se exige login para navegar.

---

### HU-O-TIENDA-002 · Ana filtra el catálogo hasta encontrar un título concreto

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `tienda` |
| **Actor** | Visitante |
| **CUs relacionados** | CU-O07, CU-O11, CU-O12 |

**Pasos:**

1. Desde `/store`, entro a **CATÁLOGO** (`/store/catalog`).
2. En el buscador escribo parte del nombre (ej. "Half-Life").
3. Opcional: filtro **Gratis** o un **género**.
4. Cambio a página 2 si hay muchos resultados.

**Resultado esperado:** Grid con juegos acotados, contador "Mostrando X–Y de Z", sin banner de error.

---

### HU-O-TIENDA-003 · Ana descubre novedades en la home de la tienda

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `tienda` |
| **Actor** | Visitante |
| **CUs relacionados** | CU-O09 |

**Precondiciones:** Semana 1+ cargada (HU-T-ETL-001).

**Pasos:**

1. Entro a `/store`.
2. Bajo hasta la sección **Nuevos lanzamientos** (debajo de destacados).
3. Veo hasta 8 tarjetas con portada, precio y enlace a ficha.
4. Hago clic en un título → `/store/game/{slug}`.

**Resultado esperado:** La sección solo aparece si hay datos (`GET /store/new-releases`). Portadas vía placeholder SVG o RAWG.

---

## Nivel operativo — Cuenta y perfil

### HU-O-AUTH-001 · Carlos se registra para comprar

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `auth` |
| **Actor** | Visitante → Usuario registrado |
| **CUs relacionados** | CU-O01, CU-O02, CU-O03-a |

**Pasos:**

1. En `/store`, pulso **Iniciar sesión** → pestaña **Registrarse**.
2. Completo nombre, email y contraseña → **Crear cuenta**.
3. Verifico que el navbar muestra mi nombre y el enlace **Carrito**.

**Resultado esperado:** Token JWT en sesión. Perfil en `/profile` muestra mi email.

---

## Nivel operativo — Wishlist

### HU-O-WISH-001 · Carlos guarda un juego para después

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `wishlist` |
| **Actor** | Usuario registrado |
| **CUs relacionados** | CU-O14, CU-O15, CU-O17 |

**Pasos:**

1. Inicio sesión y abro la ficha de un juego.
2. Pulso **Agregar a Wishlist** (icono `favorite_border`) → el botón pasa a **En tu wishlist** (`favorite`).
3. Voy a **LISTA DE DESEOS** en el navbar (`/profile`) → sección **Mi lista de deseados** con el juego.
4. Más tarde, pulso el icono **Quitar** (`close`) en la tarjeta para eliminarlo.

**Resultado esperado:** Wishlist persiste entre sesiones (Pinot REALTIME `fact_wishlist`).

---

## Nivel operativo — Carrito y pago (simulación)

### HU-O-COMPRA-001 · Carlos compra un juego con pago sandbox (sin tarjeta)

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `carrito`, `checkout`, `biblioteca` |
| **Actor** | Usuario registrado |
| **CUs relacionados** | CU-O18, CU-O19, CU-O22, CU-O23, CU-O24 |

**Precondiciones:** Login activo. Tablas REALTIME de carrito/compras creadas.

**Pasos:**

1. En la ficha del juego, **Añadir al carro**.
2. En el popup **¡Añadido a tu carro!**, el botón dice **Ver mi carro (1)** de inmediato (no `(0)`).
3. Voy a **Carrito** → **Continuar al pago** (`/payment`).
4. Reviso líneas con **portada** del juego.
5. Selecciono **Pago inmediato (sandbox)** → **Completar compra**.
6. Llego a la pantalla de **Compra completada** con opciones **Ir a biblioteca** / **Seguir explorando** (auto-redirección a biblioteca en ~5 s).

**Resultado esperado:** El juego aparece en biblioteca. Carrito vacío. Sin popup "Not Found".

> **Nota:** No hay formulario de tarjeta — es simulación demo. Stripe solo aplica si configuras `STRIPE_SECRET_KEY`.

---

### HU-O-COMPRA-002 · Carlos recarga la cartera y paga con saldo

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `wallet`, `checkout`, `biblioteca` |
| **Actor** | Usuario registrado |

**Pasos:**

1. Con juegos en el carrito, voy a **Cartera** (`/my-wallet`) desde el navbar ($ en la barra).
2. Elijo **$20** (o otro monto) → **Añadir fondos** — simula recarga Steam Wallet.
3. Veo saldo actualizado e historial con movimiento **Recarga**.
4. Vuelvo a **Continuar al pago** → elijo **Cartera GameMetrics** → **Pagar con cartera**.
5. Confirmo en biblioteca.

**Resultado esperado:** Saldo descontado. Juego en biblioteca. Mensaje de éxito, no "Not Found".

---

### HU-O-COMPRA-003 · Carlos solicita reembolso y recupera el saldo

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `refunds`, `wallet`, `biblioteca` |
| **Actor** | Usuario registrado (comprador) |
| **CUs relacionados** | CU-O24 (inverso), política 14 días |

**Precondiciones:** Compra reciente (&lt; 14 días) en biblioteca.

**Pasos:**

1. Abro **Mi biblioteca** (`/my-library`).
2. En un juego comprado, abro menú → **Solicitar reembolso**.
3. **Paso 1:** Leo política (14 días) → **Continuar**.
4. **Paso 2:** Elijo motivo (ej. "No funciona en mi equipo") → **Continuar**.
5. **Paso 3:** Confirmo checkbox → **Confirmar reembolso**.
6. Veo pantalla de éxito con importe acreditado a cartera.

**Resultado esperado:** Juego desaparece de biblioteca activa. Saldo en cartera incrementado (si `fact_user_wallets` existe). Endpoint `POST /refunds` responde 200, no 404.

---

## Nivel operativo — Reseñas (post-compra)

### HU-O-RESENA-001 · Carlos valora un juego que ya posee

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquete** | `resenas` |
| **Actor** | Comprador verificado |
| **CUs relacionados** | CU-O26, CU-O27 |

**Precondiciones:** Juego en biblioteca (HU-O-COMPRA-001).

**Pasos:**

1. Abro ficha del juego en biblioteca o `/store/game/{slug}`.
2. Si lo poseo, aparece formulario de reseña verificada.
3. Envío puntuación y texto.
4. Otros usuarios ven la reseña en la ficha (CU-O27).

**Resultado esperado:** Reseña ligada a compra verificada en `fact_reviews`.

---

## Nivel operativo — Launcher (instalar y jugar)

### HU-O-LAUNCHER-001 · Carlos instala un juego de su biblioteca y juega

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `launcher`, `biblioteca` |
| **Actor** | Usuario registrado (comprador) |
| **CUs relacionados** | CU-O28, CU-O29, CU-O30 |

**Precondiciones:** Al menos un juego en biblioteca (HU-O-COMPRA-001). Router `/launcher` activo.

**Pasos:**

1. Abro **BIBLIOTECA** (`/my-library`).
2. En un juego con estado **No instalado**, pulso **Instalar**.
3. Veo barra de progreso y estado **Descargando** hasta **Listo para jugar**.
4. Pulso **Jugar** → overlay a pantalla completa con cronómetro de sesión.
5. Pulso **Detener juego** para cerrar la sesión.
6. (Opcional) Menú → **Desinstalar** → confirmo; el juego vuelve a **No instalado** pero sigue en biblioteca.

**Resultado esperado:** `POST /launcher/install`, polling de progreso y `POST /launcher/play/stop` responden 200. Logros visibles en panel lateral del juego.

---

## Nivel operativo — Regalos

### HU-O-GIFT-001 · Carlos regala un juego a otro usuario

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `gifts`, `wallet`, `biblioteca` |
| **Actor** | Usuario registrado (remitente y destinatario) |
| **CUs relacionados** | CU-O31, CU-O32 |

**Precondiciones:** Remitente con saldo en cartera (HU-O-COMPRA-002). Destinatario registrado con otro email.

**Pasos:**

1. Inicio sesión como remitente → ficha del juego → **Regalar a un amigo**.
2. Escribo el email del destinatario y mensaje opcional → **Pagar con cartera y enviar**.
3. Veo modal de confirmación con nombre del juego y destinatario.
4. Cierro sesión e inicio como destinatario → icono **Regalos** en navbar (badge si hay pendientes).
5. Entro a **Mis regalos** (`/my-gifts`) → pestaña **Recibidos** → **Aceptar**.
6. Verifico el juego en **Mi biblioteca**.

**Resultado esperado:** Saldo descontado al remitente. Tras aceptar, juego en biblioteca del destinatario. Rechazar devuelve saldo al remitente.

---

## Nivel operativo — Social y alertas

### HU-O-SOCIAL-001 · Carlos gestiona amigos y ve notificaciones

| | |
|---|---|
| **Nivel** | Operativo |
| **Paquetes** | `social`, `alerts` |
| **Actor** | Usuario registrado |
| **CUs relacionados** | CU-O33, CU-O34 |

**Pasos:**

1. Entro a **AMIGOS** (`/my-friends`).
2. Busco otro usuario por email o nombre → envío solicitud de amistad.
3. Con la otra cuenta, acepto la solicitud.
4. En el navbar, abro el icono **Notificaciones** (`notifications`) y reviso alertas recientes (regalos, amigos, etc.).

**Resultado esperado:** Listas de amigos y solicitudes persisten. Dropdown de alertas carga sin error 404 (`GET /alerts`).

---

## Nivel estratégico — Visión gerencial (referencia)

### HU-E-BI-001 · La gerente revisa KPIs del catálogo por semana

| | |
|---|---|
| **Nivel** | Estratégico |
| **Paquete** | `dashboard` (BI) |
| **Actor** | Analista BI |
| **CUs relacionados** | CU-E01 … CU-E07 |

**Estado en demo operativa:** KPIs analíticos viven en el módulo BI archivado. En la demo actual, la **semana ETL** y métricas de carga se gestionan desde el Panel ETL en `/`. Para gráficos por género/plataforma/ESRB, reactivar router `dashboard` desde `_archivado`.

---

## Portadas de juegos (imágenes)

| Modo | Cómo funciona |
|------|----------------|
| **Sin configuración** | Placeholder **SVG local** servido por el backend (`/store/cover-placeholder/{slug}`) — iconografía Material Symbols en UI; portadas con nombre del juego en catálogo, carrito, pago, biblioteca, regalos y reembolso. |
| **Con RAWG (gratis)** | Añade `RAWG_API_KEY` en `backend/.env` ([rawg.io/apidocs](https://rawg.io/apidocs)). El backend busca portada por slug y, si falla, por nombre. |

Tras cambiar `.env`, reconstruye backend: `docker compose build backend && docker compose up -d backend`.

---

## Mapa rápido paquete → nivel

| Paquete | Nivel | Historias principales en este doc |
|---------|-------|-----------------------------------|
| `etl`, `dimensiones`, `empresa` | Táctico | HU-T-ETL-001 |
| `tienda` | Operativo | HU-O-TIENDA-001 … 003 |
| `auth` | Operativo | HU-O-AUTH-001 |
| `wishlist` | Operativo | HU-O-WISH-001 |
| `carrito`, `checkout`, `coupons` | Operativo | HU-O-COMPRA-001 |
| `wallet` | Operativo | HU-O-COMPRA-002, HU-O-GIFT-001 |
| `refunds` | Operativo | HU-O-COMPRA-003 |
| `biblioteca` | Operativo | HU-O-COMPRA-001 … 003, HU-O-LAUNCHER-001 |
| `resenas` | Operativo | HU-O-RESENA-001 |
| `launcher` | Operativo | HU-O-LAUNCHER-001 |
| `gifts` | Operativo | HU-O-GIFT-001 |
| `social`, `alerts` | Operativo | HU-O-SOCIAL-001 |
| `community`, `events` | Operativo | (foro/eventos en ficha — API activa) |
| `dashboard` (BI) | Estratégico | HU-E-BI-001 (archivado en demo) |

---

## Tests automatizados

```powershell
cd e2e
npm test
```

Cubren registro, tienda, wishlist, carrito, pago sandbox, cartera, biblioteca y contador del popup de carrito. Ampliable con reembolso, launcher, regalos y amigos.

---

## Routers API activos (`backend/main.py`)

```
/auth  /store  /user  /cart  /library  /reviews  /wishlist
/dimensiones  /empresa  /wallet  /checkout  /coupons  /refunds
/gifts  /launcher  /social  /community  /events  /alerts
```
