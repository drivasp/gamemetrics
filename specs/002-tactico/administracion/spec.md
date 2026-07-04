# Nivel Táctico — Administración de Plataforma

## 1. Nombre del paquete
**Administración** — Gestión empresarial, dimensiones y pipeline ETL

## 2. Objetivo
Permitir al Administrador gestionar las 10 colecciones empresariales (empleados, contratos, campañas, etc.) almacenadas en `emp_records` (Pinot REALTIME), y al Administrador ETL mantener las 5 dimensiones OFFLINE y ejecutar el pipeline de carga de datos.

## 3. Contexto
GameMetrics S.A. necesita gestionar su propia estructura organizacional (empleados, contratos, catálogo de distribución) dentro de la misma plataforma. La tabla `emp_records` en Pinot REALTIME actúa como un store genérico de colecciones empresariales con CRUD completo vía Kafka.

## 4. Ubicación
- **Nivel empresarial:** Táctico (002)
- **Departamento:** Administración de Plataforma
- **Paquetes:** empresa, dimensiones, etl

## 5. Actores

| Actor | Rol |
|-------|-----|
| Administrador | CRUD sobre las 10 colecciones empresariales. |
| Administrador ETL | Ejecuta pipeline de carga, crea/recarga dimensiones. |
| Analista BI | Consulta dimensiones (solo lectura). |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-T01 | Listar registros de una colección empresarial | Administrador | OE3 |
| CU-T02 | Crear registro en colección empresarial | Administrador | OE3 |
| CU-T03 | Actualizar registro en colección empresarial | Administrador | OE3 |
| CU-T04 | Eliminar registro (soft delete) de colección | Administrador | OE3 |
| CU-T05 | Consultar dimensiones OFFLINE (géneros, plataformas, etc.) | Analista BI, Administrador | OE1, OE3 |
| CU-T06 | Ejecutar pipeline ETL (carga Parquet → Pinot OFFLINE) | Administrador ETL | OE4 |
| CU-T07 | Monitorear estado de contenedores y tablas Pinot | Administrador ETL | OE4 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-ADM-001 | Como Administrador, quiero ver la lista de empleados paginada para gestionar el personal. |
| US-ADM-002 | Como Administrador, quiero crear un nuevo contrato en la plataforma para registrar acuerdos. |
| US-ADM-003 | Como Administrador, quiero actualizar datos de una campaña de marketing para mantener la información vigente. |
| US-ADM-004 | Como Administrador, quiero eliminar un registro obsoleto (soft delete) para mantener la base de datos limpia. |
| US-ADM-005 | Como Analista BI, quiero consultar la lista de géneros disponibles para usarla en filtros del dashboard. |
| US-ADM-006 | Como Administrador ETL, quiero ejecutar el script de carga ETL para actualizar el catálogo OFFLINE. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-ADM-001 | El sistema MUST proveer `GET /empresa/{collection}/records?page=N&perPage=M` para listar registros paginados de cualquiera de las 10 colecciones válidas. |
| RF-ADM-002 | El sistema MUST proveer `POST /empresa/{collection}/records` para crear un registro enviando evento Kafka al topic `emp_records`. |
| RF-ADM-003 | El sistema MUST proveer `PATCH /empresa/{collection}/records/{record_id}` para actualizar un registro con merge parcial vía Kafka. |
| RF-ADM-004 | El sistema MUST proveer `DELETE /empresa/{collection}/records/{record_id}` para eliminar un registro mediante tombstone Kafka (`deleted=TRUE`). |
| RF-ADM-005 | El sistema MUST rechazar peticiones a colecciones no válidas con HTTP 404. Las colecciones válidas son: `plataformas`, `generos`, `clasificaciones_esrb`, `desarrolladores`, `publicadores`, `empleados`, `contratos`, `catalogo_distribucion`, `campanas_marketing`, `evaluaciones_analiticas`. |
| RF-ADM-006 | El sistema MUST proveer endpoints de dimensiones (solo lectura) bajo `/dimensiones/`. |
| RF-ADM-007 | El sistema SHALL proveer una interfaz Angular (`EmpresaComponent`) con selector de colección y tabla paginada CRUD. |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-ADM-001 | Las operaciones de lectura sobre `emp_records` MUST responder en < 2 s. |
| RNF-ADM-002 | El soft delete MUST garantizar que registros eliminados no aparecen en listados (`deleted = FALSE`). |
| RNF-ADM-003 | La paginación MUST soportar hasta 200 registros por página (`perPage` máximo). |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-ADM-001 | El borrado de registros empresariales es SIEMPRE lógico (tombstone). No hay DELETE físico en Pinot. |
| RN-ADM-002 | El `record_id` es generado por el servidor (uuid4 hex de 15 caracteres). El cliente no puede asignarlo. |
| RN-ADM-003 | El campo `data_json` almacena el contenido flexible del registro como JSON serializado. |
| RN-ADM-004 | La actualización (PATCH) hace merge del `data_json` existente con los campos nuevos; no reemplaza todo. |

## 11. Entradas y salidas

| Elemento | Descripción |
|----------|-------------|
| **Entrada (crear/actualizar)** | JSON libre con campos del registro empresarial. |
| **Entrada (listar)** | `page` (int, desde 1), `perPage` (int, 1-200). |
| **Salida** | JSON con `{items, totalItems, totalPages, page, perPage}`. |

## 12. Escenarios Gherkin

**Escenario: Crear empleado**
```gherkin
Dado que el Administrador tiene un token JWT válido
Y envía POST /empresa/empleados/records con { "nombre": "Ana García", "cargo": "Analista" }
Cuando el backend procesa la petición
Entonces envía evento kafka_send("emp_records", record_id, {..., deleted: false})
Y retorna HTTP 201 con el registro creado incluyendo un record_id generado
Y el registro es visible en GET /empresa/empleados/records en < 2 segundos
```

**Escenario: Colección inválida**
```gherkin
Dado que el Administrador envía GET /empresa/nominas/records
Cuando el backend valida la colección
Entonces retorna HTTP 404 con mensaje "Colección no encontrada"
```

**Escenario: Eliminar registro (soft delete)**
```gherkin
Dado que existe un registro con id "abc123" en la colección "contratos"
Cuando el Administrador envía DELETE /empresa/contratos/records/abc123
Entonces el backend envía kafka_send("emp_records", "abc123", {..., deleted: true})
Y el registro deja de aparecer en GET /empresa/contratos/records
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-ADM-001 | POST a colección válida retorna HTTP 201 con `id` generado. |
| CA-ADM-002 | GET a colección inválida retorna HTTP 404. |
| CA-ADM-003 | DELETE de un registro hace que desaparezca del GET posterior (tras consistencia eventual). |
| CA-ADM-004 | La paginación retorna `totalPages` calculado correctamente. |
| CA-ADM-005 | PATCH hace merge parcial; campos no enviados conservan su valor anterior. |

## 14. Dependencias

| Paquete | Tipo |
|---------|------|
| `shared/kafka_producer.py` | Todas las escrituras pasan por `kafka_send`. |
| `shared/cliente_pinot.py` | Lecturas de `emp_records` y dimensiones. |
| Kafka topic `emp_records` | Topic REALTIME consumido por Pinot. |

## 15. Fuera de alcance

- Autenticación de administrador (actualmente los endpoints de empresa no requieren JWT — mejora pendiente).
- Control de acceso por rol (RBAC) sobre colecciones específicas.
- Auditoría de cambios (historial de versiones de un registro).
