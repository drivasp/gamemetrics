# Paquete biblioteca — Biblioteca de Juegos Comprados [Planificado]

## 1. Nombre del paquete
**biblioteca** — Colección Personal de Juegos Adquiridos

> **Estado:** [Planificado] — No implementado en el código actual. Las especificaciones describen el diseño objetivo.

## 2. Objetivo
Proveer al Usuario Registrado una vista de todos los juegos que ha comprado en la plataforma, derivada de los eventos de compra registrados en Pinot REALTIME (topic `purchases`). La biblioteca es de solo lectura; los registros se crean por el flujo de checkout del paquete carrito.

## 3. Contexto
Tras cada compra exitosa con Stripe sandbox, el paquete carrito emite eventos Kafka al topic `purchases`. La tabla `purchases` en Pinot REALTIME actúa como la biblioteca del usuario: contiene el historial completo de juegos adquiridos. El paquete biblioteca provee los endpoints de lectura sobre esta tabla y habilita la validación de "compra verificada" que necesita el paquete reseñas.

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Comercio
- **Paquete:** biblioteca

## 5. Actores

| Actor | Rol |
|-------|-----|
| Usuario Registrado | Consulta su biblioteca de juegos comprados. |
| Sistema (carrito) | Upstream: emite eventos de compra que alimentan la tabla `purchases`. |
| Sistema (reseñas) | Downstream: consulta `purchases` para verificar que el usuario compró el juego antes de permitir una reseña. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O24 | Ver biblioteca de juegos comprados | Usuario Registrado | OE2 |
| CU-O25 | Verificar si el usuario posee un juego (uso interno) | Sistema (reseñas, carrito) | OE2 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-LIB-001 | Como Usuario Registrado, quiero ver todos los juegos que he comprado en una sola pantalla para acceder fácilmente a mi colección. |
| US-LIB-002 | Como Usuario Registrado, quiero ver la fecha de compra de cada juego de mi biblioteca para llevar un registro de mis adquisiciones. |
| US-LIB-003 | Como Usuario Registrado, quiero que un juego comprado aparezca en mi biblioteca en menos de 2 segundos tras el pago para confirmar que la transacción fue exitosa. |
| US-LIB-004 | Como Usuario Registrado, quiero poder escribir una reseña de un juego de mi biblioteca (funcionalidad en paquete reseñas, que usa la biblioteca como fuente de verdad). |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-LIB-001 | [Planificado] El sistema MUST proveer `GET /library` protegido por JWT Bearer que retorne todos los juegos comprados por el usuario autenticado, ordenados por `purchased_at DESC`. |
| RF-LIB-002 | [Planificado] El endpoint `GET /library` MUST consultar la tabla Pinot REALTIME `purchases` filtrando por `user_id` del JWT. |
| RF-LIB-003 | [Planificado] El sistema MUST proveer `GET /library/check/{game_slug}` protegido por JWT que retorne `{owned: bool}` indicando si el usuario posee el juego. |
| RF-LIB-004 | [Planificado] El endpoint `GET /library/check/{game_slug}` MUST ser usado por el paquete carrito para prevenir compras duplicadas y por el paquete reseñas para verificar compra. |
| RF-LIB-005 | [Planificado] El módulo biblioteca MUST NO tener endpoints de escritura propios; los registros de `purchases` los crea exclusivamente el paquete carrito vía Kafka. |
| RF-LIB-006 | [Planificado] El sistema MUST registrar `library_router` en `backend/main.py` con prefijo `/library` (convención C1). |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-LIB-001 | [Planificado] `GET /library` MUST responder en menos de 1 segundo. |
| RNF-LIB-002 | [Planificado] Un juego comprado MUST aparecer en la biblioteca en menos de 2 segundos tras el evento Kafka (consistencia eventual P4). |
| RNF-LIB-003 | [Planificado] La biblioteca MUST soportar un historial ilimitado de compras por usuario (sin paginación obligatoria, pero recomendada para > 100 juegos). |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-LIB-001 | La biblioteca es inmutable desde el punto de vista del usuario: no puede eliminar juegos comprados. |
| RN-LIB-002 | Un juego comprado dos veces (error de duplicado de checkout) genera dos entradas en `purchases`; el endpoint `GET /library/check/{slug}` retorna `owned=True` si existe al menos una. |
| RN-LIB-003 | La fuente de verdad de la biblioteca es la tabla `purchases` en Pinot REALTIME; no hay otra tabla de biblioteca. |

## 11. Entradas y salidas

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| `GET /library` | Header JWT | `list[LibraryItemDTO]` |
| `GET /library/check/{slug}` | Header JWT + slug path | `{owned: bool}` |

**LibraryItemDTO:** `{purchase_id, game_slug, game_name, game_image?, amount, purchased_at}`

## 12. Escenarios Gherkin

**Escenario: Ver biblioteca (CU-O24)**
```gherkin
Dado que el Usuario ha comprado 3 juegos
Y los eventos de compra están indexados en Pinot REALTIME (purchases)
Cuando envía GET /library con JWT válido
Entonces el backend consulta purchases WHERE user_id = '{user_id}' ORDER BY purchased_at DESC
Y retorna una lista de 3 LibraryItemDTO
```

**Escenario: Juego recién comprado aparece en biblioteca**
```gherkin
Dado que el Usuario completa un checkout exitoso con Stripe sandbox
Cuando kafka_send("purchases", purchase_id, {...}) es procesado por Pinot
Entonces en menos de 2 segundos el juego aparece en GET /library
```

**Escenario: Verificar posesión de juego (uso interno)**
```gherkin
Dado que el Usuario posee el juego "hollow-knight"
Cuando el paquete carrito llama a GET /library/check/hollow-knight
Entonces retorna { "owned": true }
Y el carrito impide agregar ese juego (HTTP 409)
```

**Escenario: Biblioteca vacía**
```gherkin
Dado que el Usuario no ha comprado ningún juego
Cuando envía GET /library con JWT válido
Entonces retorna una lista vacía []
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-LIB-001 | GET /library retorna los juegos del usuario con `purchase_id`, `game_slug`, `amount` y `purchased_at`. |
| CA-LIB-002 | GET /library sin token retorna HTTP 401. |
| CA-LIB-003 | GET /library/check/{slug} retorna `{owned: true}` para un juego comprado. |
| CA-LIB-004 | GET /library/check/{slug} retorna `{owned: false}` para un juego no comprado. |
| CA-LIB-005 | Un juego aparece en GET /library en menos de 2 segundos tras su evento Kafka de compra. |
| CA-LIB-006 | No existe ningún endpoint de escritura en el módulo biblioteca. |

## 14. Dependencias

| Paquete / Recurso | Tipo |
|-------------------|------|
| `purchases` (Pinot REALTIME) | Fuente de verdad de la biblioteca; solo lectura. |
| `carrito` (003-operativo) | Upstream: emite eventos al topic `purchases`. |
| `auth` (003-operativo) | JWT para proteger los endpoints. |
| `resenas` (003-operativo) | Downstream: consume `GET /library/check/{slug}` para validar reseñas verificadas. |

## 15. Fuera de alcance

- Descargar juegos (GameMetrics es una plataforma de análisis/descubrimiento, no un servicio de distribución real).
- Devolver o transferir juegos.
- Categorizar o etiquetar juegos dentro de la biblioteca.
- Historial de actividad por juego (tiempo jugado, logros).
