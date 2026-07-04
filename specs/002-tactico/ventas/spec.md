# Nivel Táctico — Ventas y Marketing

## 1. Nombre del paquete
**Ventas** — Campañas de Marketing, Catálogo de Distribución y Pricing

## 2. Objetivo
Gestionar las colecciones empresariales orientadas a la operación comercial: campañas de marketing, catálogo de distribución y la fórmula de pricing dinámica basada en valoraciones de los juegos.

## 3. Contexto
El equipo de ventas de GameMetrics S.A. necesita administrar las campañas promocionales y el catálogo de distribución directamente desde la plataforma, usando las mismas colecciones de `emp_records`. La fórmula de precio está centralizada en el backend y se aplica consistentemente en todo el sistema.

## 4. Ubicación
- **Nivel empresarial:** Táctico (002)
- **Departamento:** Ventas y Marketing
- **Paquetes:** ventas (campanas_marketing, catalogo_distribucion en emp_records)

## 5. Actores

| Actor | Rol |
|-------|-----|
| Administrador | CRUD de campañas y catálogo de distribución. |
| Analista BI | Consulta campañas para correlacionar con KPIs. |
| Sistema | Aplica fórmula de precio a cada juego del catálogo. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-T08 | Gestionar campañas de marketing | Administrador | OE2, OE3 |
| CU-T09 | Gestionar catálogo de distribución | Administrador | OE2, OE3 |
| CU-T10 | Calcular precio de juego (fórmula automática) | Sistema | OE2 |
| CU-T11 | Ver evaluaciones analíticas | Analista BI | OE1, OE3 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-VEN-001 | Como Administrador, quiero crear una campaña de marketing para promocionar lanzamientos destacados. |
| US-VEN-002 | Como Administrador, quiero registrar juegos en el catálogo de distribución para controlar qué títulos se venden en la plataforma. |
| US-VEN-003 | Como usuario de la tienda, quiero ver el precio calculado automáticamente basado en la calidad del juego para tomar decisiones de compra. |
| US-VEN-004 | Como Analista BI, quiero consultar las evaluaciones analíticas para medir el rendimiento comercial. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-VEN-001 | El sistema MUST calcular el precio de cada juego con la fórmula: `precio = max(1.99, rating*8 + metacritic*0.4)`. Si `rating=0` y `metacritic=0` el precio es `0.00` (gratis). |
| RF-VEN-002 | El sistema MUST exponer los registros de `campanas_marketing` vía `GET/POST/PATCH/DELETE /empresa/campanas_marketing/records`. |
| RF-VEN-003 | El sistema MUST exponer los registros de `catalogo_distribucion` vía `GET/POST/PATCH/DELETE /empresa/catalogo_distribucion/records`. |
| RF-VEN-004 | El sistema MUST exponer los registros de `evaluaciones_analiticas` vía `GET/POST/PATCH/DELETE /empresa/evaluaciones_analiticas/records`. |
| RF-VEN-005 | El precio MUST mostrarse en la tarjeta de cada juego en la tienda (paquete tienda). |
| RF-VEN-006 | Los juegos con precio `0.00` MUST etiquetarse como "GRATIS" en la UI. |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-VEN-001 | El cálculo de precio es una operación CPU-bound local; MUST completarse en < 1 ms por juego. |
| RNF-VEN-002 | Las colecciones empresariales de ventas MUST seguir el mismo modelo de consistencia eventual de `emp_records`. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-VEN-001 | La fórmula de precio es fija y global: `price = max(1.99, rating*8 + metacritic*0.4)`. No puede cambiarse por campaña individual. |
| RN-VEN-002 | Un juego con `rating=0` Y `metacritic=0` es gratuito (`price=0.00`). Si solo uno es 0, se aplica la fórmula. |
| RN-VEN-003 | El precio mínimo para juegos de pago es $1.99. |

## 11. Entradas y salidas

| Elemento | Descripción |
|----------|-------------|
| **Entrada (precio)** | `rating` (float 0-5), `metacritic` (int 0-100) desde `fact_videogames`. |
| **Salida (precio)** | `price` (float, 2 decimales), `is_free` (bool). |
| **Entrada (campañas)** | JSON libre con campos de la campaña. |
| **Salida (campañas)** | Registro con `id`, `created_at` y campos de la campaña. |

## 12. Escenarios Gherkin

**Escenario: Precio de juego popular**
```gherkin
Dado que un juego tiene rating=4.5 y metacritic=92
Cuando el sistema calcula el precio
Entonces price = max(1.99, 4.5*8 + 92*0.4) = max(1.99, 36.0 + 36.8) = max(1.99, 72.8) = 72.80
Y is_free = false
```

**Escenario: Juego gratis**
```gherkin
Dado que un juego tiene rating=0 y metacritic=0
Cuando el sistema calcula el precio
Entonces price = 0.00
Y is_free = true
Y el juego aparece con etiqueta "GRATIS" en la tienda
```

**Escenario: Crear campaña de marketing**
```gherkin
Dado que el Administrador envía POST /empresa/campanas_marketing/records con datos de campaña
Cuando el backend procesa la petición
Entonces crea un registro vía kafka_send en emp_records con collection="campanas_marketing"
Y retorna HTTP 201
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-VEN-001 | Un juego con rating=4.5, metacritic=92 muestra precio=$72.80. |
| CA-VEN-002 | Un juego con rating=0, metacritic=0 muestra precio=$0.00 y etiqueta "GRATIS". |
| CA-VEN-003 | El precio mínimo mostrado para juegos de pago es $1.99. |
| CA-VEN-004 | POST a `campanas_marketing` retorna HTTP 201 con `id` generado. |

## 14. Dependencias

| Paquete | Tipo |
|---------|------|
| `store/calcular_precio.py` | Implementación de la fórmula de precio. |
| `empresa/endpoints.py` | CRUD genérico para colecciones empresariales. |
| `fact_videogames` (Pinot OFFLINE) | Fuente de `rating` y `metacritic`. |

## 15. Fuera de alcance

- Precios dinámicos por campaña o descuentos individuales.
- Integración con pasarelas de pago (eso es paquete carrito).
- Exportación de catálogo de distribución a formatos externos.
