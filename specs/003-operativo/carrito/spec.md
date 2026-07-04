# Paquete carrito — Carrito y Pago con Stripe Sandbox [Planificado]

## 1. Nombre del paquete
**carrito** — Carrito de Compras y Flujo de Pago (Stripe Sandbox)

> **Estado:** [Planificado] — No implementado en el código actual. Las especificaciones describen el diseño objetivo para la siguiente etapa de desarrollo.

## 2. Objetivo
Permitir al Usuario Registrado agregar juegos a un carrito de compras, ver su contenido, eliminar items y completar una compra simulada con Stripe en modo sandbox/mock. Al confirmar el pago, los juegos comprados se registran en la biblioteca del usuario mediante Kafka → Pinot REALTIME.

## 3. Contexto
GameMetrics S.A. planifica monetizar el catálogo mediante venta directa de videojuegos. El carrito es el paso intermedio entre la wishlist/tienda y la biblioteca. El pago usa Stripe en modo sandbox para demostración sin claves reales ni cargos reales. Toda transacción de compra genera un evento Kafka que alimenta la tabla `purchases` en Pinot REALTIME.

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Comercio
- **Paquete:** carrito

## 5. Actores

| Actor | Rol |
|-------|-----|
| Usuario Registrado | Agrega, revisa y vacía el carrito; inicia el pago. |
| Sistema (Stripe sandbox) | Procesa el pago simulado y retorna confirmación. |
| Sistema (Kafka producer) | Emite eventos de compra al topic `purchases`. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O18 | Agregar juego al carrito | Usuario Registrado | OE2 |
| CU-O19 | Ver contenido del carrito | Usuario Registrado | OE2 |
| CU-O20 | Eliminar juego del carrito | Usuario Registrado | OE2 |
| CU-O21 | Vaciar carrito completo | Usuario Registrado | OE2 |
| CU-O22 | Iniciar checkout con Stripe sandbox | Usuario Registrado | OE2 |
| CU-O23 | Confirmar pago y registrar compras | Sistema | OE2 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-CART-001 | Como Usuario Registrado, quiero agregar juegos a mi carrito para preparar una compra. |
| US-CART-002 | Como Usuario Registrado, quiero ver el contenido de mi carrito con el precio total para decidir antes de pagar. |
| US-CART-003 | Como Usuario Registrado, quiero eliminar un juego del carrito si cambio de opinión. |
| US-CART-004 | Como Usuario Registrado, quiero vaciar el carrito completo con un solo clic. |
| US-CART-005 | Como Usuario Registrado, quiero completar el pago con Stripe para adquirir los juegos del carrito. |
| US-CART-006 | Como Usuario Registrado, quiero que los juegos comprados aparezcan automáticamente en mi biblioteca tras el pago. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-CART-001 | [Planificado] El sistema MUST proveer `POST /cart/items` protegido por JWT que acepte `{game_slug, game_name, game_image?, game_price}` y agregue el juego al carrito del usuario. |
| RF-CART-002 | [Planificado] El sistema MUST proveer `GET /cart` protegido por JWT que retorne todos los items del carrito con subtotales y total. |
| RF-CART-003 | [Planificado] El sistema MUST proveer `DELETE /cart/items/{game_slug}` protegido por JWT para eliminar un item del carrito. |
| RF-CART-004 | [Planificado] El sistema MUST proveer `DELETE /cart` protegido por JWT para vaciar el carrito completo. |
| RF-CART-005 | [Planificado] El sistema MUST proveer `POST /cart/checkout` protegido por JWT que inicie una sesión de pago con Stripe sandbox y retorne una URL de confirmación o un intent de pago. |
| RF-CART-006 | [Planificado] Al confirmar el pago, el sistema MUST emitir un evento `kafka_send("purchases", purchase_id, {...})` por cada juego comprado, con campos `purchase_id`, `user_id`, `game_slug`, `amount`, `purchased_at`. |
| RF-CART-007 | [Planificado] El sistema MUST verificar que el usuario no compre un juego que ya posee en su biblioteca antes de procesar el pago. |
| RF-CART-008 | [Planificado] El carrito MUST persistirse en una nueva tabla REALTIME `fact_cart` en Pinot, con la misma arquitectura Kafka → Pinot que wishlist. |
| RF-CART-009 | [Planificado] El sistema MUST usar Stripe en modo sandbox únicamente; MUST rechazar integración con claves de producción en el entorno de desarrollo. |
| RF-CART-010 | [Planificado] El sistema MUST registrar los routers `cart/` en `backend/main.py` siguiendo la convención C1. |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-CART-001 | [Planificado] El checkout con Stripe sandbox MUST completarse en menos de 5 segundos. |
| RNF-CART-002 | [Planificado] Los eventos de compra MUST ser idempotentes: un `purchase_id` duplicado no genera un cargo doble. |
| RNF-CART-003 | [Planificado] Las claves de Stripe sandbox MUST vivir solo en variables de entorno del backend (principio P5). |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-CART-001 | Un usuario no puede agregar al carrito un juego que ya posee en su biblioteca. |
| RN-CART-002 | Un usuario no puede agregar el mismo juego dos veces al carrito (verificación por `{user_id}_{game_slug}`). |
| RN-CART-003 | El precio del juego en el carrito se fija en el momento de agregarlo y no cambia hasta el checkout. |
| RN-CART-004 | El carrito se vacía automáticamente tras un checkout exitoso. |
| RN-CART-005 | En modo sandbox, todos los pagos se simulan como exitosos con la tarjeta de prueba de Stripe. |

## 11. Entradas y salidas

| Endpoint | Entrada | Salida |
|----------|---------|--------|
| `POST /cart/items` | JWT + `{game_slug, game_name, game_image?, game_price}` | `CartItemDTO` (HTTP 201) |
| `GET /cart` | JWT | `CartDTO {items: [CartItemDTO], total: float}` |
| `DELETE /cart/items/{slug}` | JWT + slug | HTTP 204 |
| `DELETE /cart` | JWT | HTTP 204 |
| `POST /cart/checkout` | JWT | `{checkout_url?: str, payment_intent?: str, status: str}` |

**CartItemDTO:** `{id, game_slug, game_name, game_image?, game_price, added_at}`

## 12. Escenarios Gherkin

**Escenario: Agregar juego al carrito (CU-O18)**
```gherkin
Dado que el Usuario tiene un JWT válido
Y el juego "hollow-knight" NO está en su biblioteca
Y el juego NO está ya en su carrito
Cuando envía POST /cart/items con { game_slug: "hollow-knight", game_name: "Hollow Knight", game_price: 14.99 }
Entonces el backend envía kafka_send("fact_cart", "{user_id}_hollow-knight", {...})
Y retorna HTTP 201 con CartItemDTO
```

**Escenario: Checkout exitoso (CU-O22 y CU-O23)**
```gherkin
Dado que el carrito tiene 2 juegos por un total de $29.98
Cuando el Usuario envía POST /cart/checkout con JWT válido
Entonces el backend llama a la API de Stripe sandbox
Y Stripe retorna confirmación de pago simulado
Y el backend emite kafka_send("purchases", purchase_id, {...}) por cada juego
Y el carrito se vacía (tombstone en fact_cart)
Y los juegos aparecen en la biblioteca del usuario en < 2 segundos
```

**Escenario: Agregar juego ya comprado**
```gherkin
Dado que el usuario ya posee "hollow-knight" en su biblioteca
Cuando intenta agregar "hollow-knight" al carrito
Entonces retorna HTTP 409 con "Ya posees este juego en tu biblioteca"
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-CART-001 | POST /cart/items agrega el juego y retorna HTTP 201. |
| CA-CART-002 | GET /cart retorna todos los items con el total calculado correctamente. |
| CA-CART-003 | DELETE /cart/items/{slug} elimina el item y retorna HTTP 204. |
| CA-CART-004 | POST /cart/checkout con Stripe sandbox retorna confirmación sin error. |
| CA-CART-005 | Los juegos comprados aparecen en GET /library en < 2 segundos tras el checkout. |
| CA-CART-006 | Un juego ya en biblioteca no puede agregarse al carrito (HTTP 409). |
| CA-CART-007 | El mismo juego no puede estar dos veces en el carrito (HTTP 409). |
| CA-CART-008 | Stripe sandbox no requiere claves de producción ni cargos reales. |

## 14. Dependencias

| Paquete / Recurso | Tipo |
|-------------------|------|
| `auth` (003-operativo) | JWT para proteger todos los endpoints. |
| `biblioteca` (003-operativo) | Downstream: recibe los eventos de compra. |
| `fact_cart` (Pinot REALTIME) | [Planificado] Nueva tabla para el carrito. |
| Kafka topic `purchases` | [Planificado] Topic de eventos de compra. |
| Kafka topic `fact_cart` | [Planificado] Topic del carrito. |
| Stripe SDK (Python) | [Planificado] Integración de pagos en sandbox. |
| `tienda` (003-operativo) | Fuente del precio y datos del juego. |

## 15. Fuera de alcance

- Pagos reales en producción (solo sandbox/mock en la fase actual).
- Descuentos, cupones o promociones.
- Reembolsos y devoluciones.
- Gestión de impuestos o IVA.
- Múltiples métodos de pago (solo tarjeta de prueba Stripe).
- Historial de transacciones con facturación.
