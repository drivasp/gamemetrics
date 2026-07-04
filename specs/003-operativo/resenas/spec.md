# Paquete resenas — Reseñas Verificadas [Planificado]

## 1. Nombre del paquete
**resenas** — Reseñas de Videojuegos (Solo Compradores Verificados)

> **Estado:** [Planificado] — No implementado en el código actual. Las especificaciones describen el diseño objetivo.

## 2. Objetivo
Permitir que los Usuarios Registrados que han comprado un juego escriban una reseña con puntuación (1-5 estrellas) y comentario. La verificación de compra se realiza cruzando con la tabla `purchases` (via el endpoint `GET /library/check/{slug}` del paquete biblioteca). Las reseñas son visibles para todos los usuarios y se almacenan en Pinot REALTIME via Kafka.

## 3. Contexto
Las reseñas verificadas aumentan la confianza de los compradores potenciales. El modelo "solo compradores pueden reseñar" es estándar en plataformas como Steam. La validación cruzada contra `purchases` garantiza que la reseña proviene de un usuario que efectivamente adquirió el juego. El borrado de reseñas es lógico (tombstone), manteniendo la trazabilidad.

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Comercio
- **Paquete:** resenas

## 5. Actores

| Actor | Rol |
|-------|-----|
| Usuario Registrado (comprador) | Puede crear, editar y eliminar sus propias reseñas. |
| Visitante | Puede leer las reseñas de un juego sin autenticación. |
| Administrador | Puede eliminar cualquier reseña (moderación). |
| Sistema (biblioteca) | Valida que el usuario es comprador antes de crear una reseña. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O26 | Crear reseña verificada de un juego | Usuario Registrado (comprador) | OE2 |
| CU-O27 | Leer reseñas de un juego | Visitante, Usuario Registrado | OE2 |
| CU-O28 | Editar propia reseña | Usuario Registrado (comprador) | OE2 |
| CU-O29 | Eliminar propia reseña (soft delete) | Usuario Registrado (comprador) | OE2 |
| CU-O30 | Moderar reseña (eliminar) | Administrador | OE3 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-REV-001 | Como comprador, quiero escribir una reseña del juego que compré para compartir mi experiencia con otros usuarios. |
| US-REV-002 | Como comprador, quiero calificar el juego con 1-5 estrellas para resumir mi valoración de forma rápida. |
| US-REV-003 | Como Visitante, quiero leer las reseñas de un juego antes de comprarlo para tomar una decisión informada. |
| US-REV-004 | Como comprador, quiero editar mi reseña si cambio de opinión o quiero corregir algo. |
| US-REV-005 | Como comprador, quiero eliminar mi reseña si ya no deseo mantenerla. |
| US-REV-006 | Como Visitante, quiero ver el rating promedio de un juego basado en reseñas verificadas para tener una referencia objetiva. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-REV-001 | [Planificado] El sistema MUST proveer `POST /reviews/{game_slug}` protegido por JWT que acepte `{rating: int (1-5), comment: str}` y cree una reseña. |
| RF-REV-002 | [Planificado] El endpoint `POST /reviews/{game_slug}` MUST verificar que el usuario ha comprado el juego consultando `purchases` (o `GET /library/check/{slug}`); si no lo ha comprado, MUST retornar HTTP 403. |
| RF-REV-003 | [Planificado] El endpoint `POST /reviews/{game_slug}` MUST verificar que el usuario no tiene ya una reseña activa del mismo juego; si ya existe, MUST retornar HTTP 409. |
| RF-REV-004 | [Planificado] El sistema MUST proveer `GET /reviews/{game_slug}` público (sin JWT) que retorne todas las reseñas activas del juego, ordenadas por `created_at DESC`. |
| RF-REV-005 | [Planificado] El endpoint `GET /reviews/{game_slug}` SHOULD incluir el rating promedio y el total de reseñas en la respuesta. |
| RF-REV-006 | [Planificado] El sistema MUST proveer `PUT /reviews/{game_slug}` protegido por JWT que permita al autor editar su propia reseña (`rating` y/o `comment`). |
| RF-REV-007 | [Planificado] El sistema MUST proveer `DELETE /reviews/{game_slug}` protegido por JWT que permita al autor eliminar su reseña mediante tombstone Kafka (`deleted=True`). |
| RF-REV-008 | [Planificado] Toda escritura de reseña MUST pasar por `kafka_send("reviews", review_id, {...})` (principio P1). |
| RF-REV-009 | [Planificado] El `review_id` MUST construirse como `{user_id}_{game_slug}` para garantizar unicidad de una reseña por usuario por juego. |
| RF-REV-010 | [Planificado] El sistema MUST registrar `reviews_router` en `backend/main.py` con prefijo `/reviews` (convención C1). |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-REV-001 | [Planificado] `GET /reviews/{game_slug}` MUST responder en menos de 1 segundo. |
| RNF-REV-002 | [Planificado] Una reseña creada MUST ser visible en `GET /reviews/{game_slug}` en menos de 2 segundos (consistencia eventual P4). |
| RNF-REV-003 | [Planificado] El campo `comment` SHOULD tener un límite máximo de 2000 caracteres. |
| RNF-REV-004 | [Planificado] El rating MUST ser un entero entre 1 y 5 inclusive; valores fuera de rango retornan HTTP 422. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-REV-001 | Solo usuarios que han comprado el juego pueden crear una reseña (reseña verificada). |
| RN-REV-002 | Un usuario solo puede tener una reseña activa por juego. Para modificar su opinión, edita la reseña existente. |
| RN-REV-003 | El `review_id` es `{user_id}_{game_slug}`, garantizando unicidad por usuario y juego como clave de upsert en Pinot. |
| RN-REV-004 | El borrado de reseñas es lógico (tombstone `deleted=True` vía Kafka); los registros no se eliminan de Pinot. |
| RN-REV-005 | El rating promedio se calcula en tiempo de consulta sobre `reviews` en Pinot (`AVG(rating) WHERE game_slug=... AND deleted=FALSE`). |
| RN-REV-006 | Un usuario solo puede editar o eliminar sus propias reseñas (verificado por `user_id` del JWT). |

## 11. Entradas y salidas

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| `POST /reviews/{game_slug}` | JWT + `{rating: int, comment: str}` | `ReviewDTO` (HTTP 201) |
| `GET /reviews/{game_slug}` | (público) | `ReviewPageDTO {reviews: [ReviewDTO], avg_rating: float, total: int}` |
| `PUT /reviews/{game_slug}` | JWT + `{rating?: int, comment?: str}` | `ReviewDTO` |
| `DELETE /reviews/{game_slug}` | JWT | HTTP 204 |

**ReviewDTO:** `{review_id, user_id, game_slug, rating: int, comment: str, created_at, display_name?}`

## 12. Escenarios Gherkin

**Escenario: Crear reseña verificada (CU-O26)**
```gherkin
Dado que el Usuario tiene JWT válido
Y ha comprado el juego "hollow-knight" (existe en purchases con user_id del token)
Y no tiene reseña previa de ese juego
Cuando envía POST /reviews/hollow-knight con { rating: 5, comment: "Obra maestra" }
Entonces el backend verifica posesión en purchases → found
Y construye review_id = "{user_id}_hollow-knight"
Y emite kafka_send("reviews", review_id, { ..., deleted: false })
Y retorna HTTP 201 con ReviewDTO
Y la reseña aparece en GET /reviews/hollow-knight en < 2 segundos
```

**Escenario: Intento de reseña sin compra**
```gherkin
Dado que el Usuario tiene JWT válido
Pero NO ha comprado el juego "elden-ring"
Cuando envía POST /reviews/elden-ring con { rating: 4, comment: "Me parece" }
Entonces el backend consulta purchases y no encuentra compra del usuario
Y retorna HTTP 403 con "Debes comprar el juego para poder reseñarlo"
Y NO emite evento Kafka
```

**Escenario: Reseña duplicada**
```gherkin
Dado que el Usuario ya tiene una reseña activa de "hollow-knight"
Cuando intenta crear otra reseña de "hollow-knight"
Entonces retorna HTTP 409 con "Ya tienes una reseña de este juego"
```

**Escenario: Ver reseñas de un juego (CU-O27)**
```gherkin
Dado que el juego "hollow-knight" tiene 3 reseñas con ratings [5, 4, 4]
Cuando el Visitante llama a GET /reviews/hollow-knight (sin JWT)
Entonces retorna ReviewPageDTO con reviews ordenadas por created_at DESC
Y avg_rating = 4.33
Y total = 3
```

**Escenario: Eliminar propia reseña (CU-O29)**
```gherkin
Dado que el Usuario tiene una reseña de "hollow-knight"
Cuando envía DELETE /reviews/hollow-knight con JWT
Entonces el backend envía kafka_send("reviews", review_id, {..., deleted: True})
Y retorna HTTP 204
Y la reseña ya no aparece en GET /reviews/hollow-knight
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-REV-001 | POST /reviews/{slug} de comprador válido retorna HTTP 201 con ReviewDTO. |
| CA-REV-002 | POST /reviews/{slug} de no-comprador retorna HTTP 403. |
| CA-REV-003 | POST /reviews/{slug} duplicado retorna HTTP 409. |
| CA-REV-004 | GET /reviews/{slug} (sin JWT) retorna lista de reseñas con avg_rating y total. |
| CA-REV-005 | PUT /reviews/{slug} actualiza rating y/o comment de la reseña del usuario. |
| CA-REV-006 | PUT /reviews/{slug} de reseña de otro usuario retorna HTTP 403. |
| CA-REV-007 | DELETE /reviews/{slug} retorna HTTP 204 y tombstone en Kafka. |
| CA-REV-008 | Rating fuera del rango 1-5 retorna HTTP 422. |
| CA-REV-009 | La reseña aparece en GET /reviews/{slug} en menos de 2 segundos tras su creación. |

## 14. Dependencias

| Paquete / Recurso | Tipo |
|-------------------|------|
| `auth` (003-operativo) | JWT para proteger endpoints de escritura. |
| `biblioteca` / `purchases` (Pinot REALTIME) | Validación de compra verificada antes de crear reseña. |
| `carrito` (003-operativo) | Upstream: emite los eventos de compra necesarios para la verificación. |
| `reviews` (Pinot REALTIME) | [Planificado] Nueva tabla REALTIME para las reseñas. |
| Kafka topic `reviews` | [Planificado] Topic de eventos de reseñas. |
| `tienda` (003-operativo) | Downstream: el detalle del juego mostrará las reseñas de este módulo. |

## 15. Fuera de alcance

- Sistema de votos o "útil/no útil" en reseñas.
- Moderación automática con análisis de sentimiento o filtros de spam.
- Reseñas de texto sin puntuación (rating es obligatorio).
- Imágenes o videos adjuntos a reseñas.
- Respuestas a reseñas (comentarios sobre comentarios).
- Notificaciones al autor del juego cuando recibe una reseña.
