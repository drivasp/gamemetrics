# Paquete wishlist — Lista de Deseos [Implementado]

## 1. Nombre del paquete
**wishlist** — Agregar, Consultar y Eliminar Juegos de la Lista de Deseos

## 2. Objetivo
Permitir al Usuario Registrado gestionar su lista de deseos personal: agregar juegos desde la tienda, ver todos los juegos en su wishlist y eliminar entradas. Toda escritura usa el patrón Kafka → Pinot REALTIME (`fact_wishlist`) con upsert idempotente. El borrado es lógico (tombstone).

## 3. Contexto
La lista de deseos es una funcionalidad clave de retención de usuarios. El modelo usa una clave compuesta `{user_id}_{game_slug}` que garantiza unicidad por usuario y juego, y permite upsert idempotente en Pinot REALTIME. El borrado físico no existe en Pinot: se envía un evento Kafka con `deleted=TRUE` (tombstone).

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Tienda
- **Paquete:** wishlist (bajo `/user/wishlist`)

## 5. Actores

| Actor | Rol |
|-------|-----|
| Usuario Registrado | Agrega, consulta y elimina juegos de su wishlist. |
| Sistema (Kafka producer) | Emite eventos al topic `fact_wishlist` para persistencia. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O14 | Agregar juego a wishlist | Usuario Registrado | OE2 |
| CU-O15 | Ver lista de deseos | Usuario Registrado | OE2 |
| CU-O16 | Verificar si un juego está en wishlist | Usuario Registrado | OE2 |
| CU-O17 | Eliminar juego de wishlist (soft delete) | Usuario Registrado | OE2 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-WISH-001 | Como Usuario Registrado, quiero agregar un juego a mi wishlist desde la página de detalle para guardarlo para más tarde. |
| US-WISH-002 | Como Usuario Registrado, quiero ver todos los juegos en mi wishlist para recordar cuáles me interesaron. |
| US-WISH-003 | Como Usuario Registrado, quiero saber si un juego ya está en mi wishlist cuando veo su detalle para no agregarlo dos veces. |
| US-WISH-004 | Como Usuario Registrado, quiero eliminar un juego de mi wishlist cuando ya no me interesa. |
| US-WISH-005 | Como Usuario Registrado, quiero que mi wishlist persista entre sesiones (no se pierde al cerrar el navegador). |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-WISH-001 | El sistema MUST proveer `POST /user/wishlist` protegido por JWT Bearer que acepte `AddWishlistDTO {game_slug, game_name, game_image?, game_price}` y agregue el juego a la wishlist del usuario autenticado. |
| RF-WISH-002 | El endpoint `POST /user/wishlist` MUST verificar si el juego ya está en la wishlist; si ya existe, MUST retornar HTTP 409. |
| RF-WISH-003 | El endpoint `POST /user/wishlist` MUST construir el `wishlist_id` como `{user_id}_{game_slug}` y emitir `kafka_send("fact_wishlist", wishlist_id, {...})`. |
| RF-WISH-004 | El sistema MUST proveer `GET /user/wishlist` protegido por JWT Bearer que retorne todos los items de la wishlist del usuario autenticado, ordenados por `created_at DESC`. |
| RF-WISH-005 | El endpoint `GET /user/wishlist` MUST filtrar por `user_id` del JWT y retornar máximo 500 items. |
| RF-WISH-006 | El sistema MUST proveer `GET /user/wishlist/check/{game_slug}` protegido por JWT Bearer que retorne `{in_wishlist: bool}` para verificar si un juego está en la wishlist. |
| RF-WISH-007 | El endpoint `GET /user/wishlist/check/{game_slug}` MUST estar registrado ANTES de `DELETE /user/wishlist/{game_slug}` en el router para evitar colisión de rutas (convención C2). |
| RF-WISH-008 | El sistema MUST proveer `DELETE /user/wishlist/{game_slug}` protegido por JWT Bearer que envíe un tombstone Kafka con `deleted=True`. |
| RF-WISH-009 | El endpoint `DELETE /user/wishlist/{game_slug}` MUST verificar que el item existe antes de enviar el tombstone; si no existe, MUST retornar HTTP 404. |
| RF-WISH-010 | El endpoint `DELETE /user/wishlist/{game_slug}` MUST retornar HTTP 204 (sin cuerpo) en caso de éxito. |
| RF-WISH-011 | Todos los endpoints de wishlist MUST validar el JWT Bearer antes de operar; token inválido o ausente retorna HTTP 401. |
| RF-WISH-012 | Toda entrada de texto (user_id, game_slug) MUST pasar por `_esc()` antes de usarse en queries Pinot (C3). |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-WISH-001 | El item agregado MUST ser visible en `GET /user/wishlist` en menos de 2 segundos tras el `POST` (consistencia eventual P4). |
| RNF-WISH-002 | `GET /user/wishlist` MUST responder en menos de 1 segundo para hasta 500 items. |
| RNF-WISH-003 | El tombstone de eliminación MUST reflejarse en Pinot REALTIME en menos de 2 segundos. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-WISH-001 | Un mismo usuario no puede agregar el mismo juego dos veces a su wishlist (verificación por `wishlist_id`). |
| RN-WISH-002 | El `wishlist_id` es `{user_id}_{game_slug}`; actúa como clave de upsert en Pinot REALTIME. |
| RN-WISH-003 | El borrado de items de wishlist es SIEMPRE lógico (tombstone); no hay DELETE físico en Pinot. |
| RN-WISH-004 | El precio (`game_price`) almacenado en la wishlist es el precio en el momento de agregar; puede diferir si la fórmula cambia (actualmente no cambia). |
| RN-WISH-005 | La wishlist está limitada a 500 items por usuario por consulta; no hay restricción de escritura. |

## 11. Entradas y salidas

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| `POST /user/wishlist` | Header JWT + `{game_slug, game_name, game_image?, game_price}` | `WishlistItemDTO` (HTTP 201) |
| `GET /user/wishlist` | Header JWT | `list[WishlistItemDTO]` |
| `GET /user/wishlist/check/{slug}` | Header JWT + slug en path | `{in_wishlist: bool}` |
| `DELETE /user/wishlist/{slug}` | Header JWT + slug en path | HTTP 204 (sin cuerpo) |

**WishlistItemDTO:** `{id: str, game_slug: str, game_name: str, game_image?: str, game_price: float, added_at?: str}`

## 12. Escenarios Gherkin

**Escenario: Agregar juego a wishlist (CU-O14)**
```gherkin
Dado que el Usuario Registrado tiene un JWT válido
Y el juego con slug "hollow-knight" no está en su wishlist
Cuando envía POST /user/wishlist con { game_slug: "hollow-knight", game_name: "Hollow Knight", game_price: 14.99 }
Entonces el backend construye wishlist_id = "{user_id}_hollow-knight"
Y verifica que no existe en fact_wishlist
Y envía kafka_send("fact_wishlist", wishlist_id, { ..., deleted: false (implícito) })
Y retorna HTTP 201 con WishlistItemDTO
Y el juego aparece en GET /user/wishlist en menos de 2 segundos
```

**Escenario: Agregar juego duplicado**
```gherkin
Dado que "hollow-knight" ya está en la wishlist del usuario
Cuando envía POST /user/wishlist con el mismo game_slug
Entonces retorna HTTP 409 con "El juego ya está en tu wishlist"
Y NO emite evento Kafka
```

**Escenario: Ver wishlist (CU-O15)**
```gherkin
Dado que el Usuario tiene 3 juegos en su wishlist
Cuando envía GET /user/wishlist con JWT válido
Entonces el backend consulta fact_wishlist WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 500
Y retorna una lista de 3 WishlistItemDTO
```

**Escenario: Verificar si juego está en wishlist (CU-O16)**
```gherkin
Dado que "hollow-knight" está en la wishlist del usuario
Cuando envía GET /user/wishlist/check/hollow-knight con JWT válido
Entonces retorna { "in_wishlist": true }
```

**Escenario: Eliminar juego de wishlist (CU-O17)**
```gherkin
Dado que "hollow-knight" está en la wishlist del usuario
Cuando envía DELETE /user/wishlist/hollow-knight con JWT válido
Entonces el backend verifica que existe en fact_wishlist
Y envía kafka_send("fact_wishlist", wishlist_id, { ..., deleted: true, game_name: "", game_image: "", game_price: 0.0 })
Y retorna HTTP 204 sin cuerpo
Y el juego ya no aparece en GET /user/wishlist tras la consistencia eventual
```

**Escenario: Eliminar juego que no está en wishlist**
```gherkin
Dado que "juego-no-en-wishlist" no está en la wishlist del usuario
Cuando envía DELETE /user/wishlist/juego-no-en-wishlist
Entonces retorna HTTP 404 con "No encontrado en wishlist"
```

**Escenario: Acceso sin token**
```gherkin
Dado que el Visitante no tiene token JWT
Cuando envía POST /user/wishlist sin header Authorization
Entonces retorna HTTP 401 con "Token requerido"
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-WISH-001 | POST /user/wishlist con juego nuevo retorna HTTP 201 con WishlistItemDTO. |
| CA-WISH-002 | POST /user/wishlist con juego ya en wishlist retorna HTTP 409. |
| CA-WISH-003 | GET /user/wishlist retorna la lista de juegos del usuario en orden cronológico inverso. |
| CA-WISH-004 | GET /user/wishlist sin token retorna HTTP 401. |
| CA-WISH-005 | GET /user/wishlist/check/{slug} retorna `{in_wishlist: true}` si el juego está en la wishlist. |
| CA-WISH-006 | GET /user/wishlist/check/{slug} retorna `{in_wishlist: false}` si el juego NO está. |
| CA-WISH-007 | DELETE /user/wishlist/{slug} retorna HTTP 204 cuando el item existía. |
| CA-WISH-008 | DELETE /user/wishlist/{slug} retorna HTTP 404 cuando el item no existía. |
| CA-WISH-009 | El item agregado es visible en GET /user/wishlist en menos de 2 segundos (consistencia eventual). |
| CA-WISH-010 | El item eliminado desaparece de GET /user/wishlist en menos de 2 segundos (tombstone procesado). |

## 14. Dependencias

| Paquete / Recurso | Tipo |
|-------------------|------|
| `fact_wishlist` (Pinot REALTIME) | Almacenamiento de la wishlist con upsert por `wishlist_id`. |
| Kafka topic `fact_wishlist` | Escritura vía `kafka_send`; clave de upsert = `wishlist_id`. |
| `auth` (003-operativo) | `verify_token()` para validar JWT en todos los endpoints. |
| `shared/kafka_producer.py` | `kafka_send()`. |
| `shared/cliente_pinot.py` | `pinot_query()` para lecturas. |
| `tienda` (003-operativo) | El detalle del juego invoca `GET /user/wishlist/check/{slug}` para mostrar el botón de wishlist. |

## 15. Fuera de alcance

- Wishlist pública compartible con otros usuarios.
- Notificaciones cuando un juego de la wishlist baja de precio o sale a la venta.
- Ordenamiento o filtros dentro de la wishlist.
- Mover juegos de la wishlist al carrito (planificado en paquete carrito).
- Límite máximo de items por wishlist (actualmente sin límite en escritura).
