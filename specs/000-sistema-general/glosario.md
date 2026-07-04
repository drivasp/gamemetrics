# Glosario del Sistema — GameMetrics S.A.

| Término | Definición |
|---------|------------|
| **Apache Pinot** | Motor OLAP columnar distribuido usado como fuente de verdad analítica. Soporta tablas OFFLINE (Parquet) y REALTIME (Kafka). |
| **Pinot OFFLINE** | Tabla Pinot cargada desde archivos Parquet. Inmutable entre cargas. Usada para `fact_videogames` y las 5 dimensiones. Filtrada por `semana`. |
| **Pinot REALTIME** | Tabla Pinot alimentada directamente desde Kafka con baja latencia (< 2 s). Usada para `fact_users`, `fact_wishlist`, `emp_records`. |
| **Upsert** | Operación de insert-or-update en Pinot REALTIME: si ya existe un registro con la misma clave primaria, lo actualiza; si no, lo inserta. |
| **Tombstone** | Mecanismo de borrado lógico en Pinot REALTIME. Se envía un evento Kafka con `deleted=TRUE`; Pinot elimina el registro usando `deleteRecordColumn`. No hay DELETE físico. |
| **Kafka** | Broker de mensajería distribuida. Cada escritura transaccional en GameMetrics produce un mensaje a un topic Kafka, que Pinot consume vía conector REALTIME. |
| **Kafka producer** | Componente del backend FastAPI (`shared/kafka_producer.py`) que envía eventos al broker Kafka mediante `kafka_send(topic, key, payload)`. |
| **kafka_send** | Función async del backend que serializa el payload a JSON y publica en el topic Kafka indicado, usando la clave para garantizar upsert idempotente. |
| **fact_users** | Tabla REALTIME en Pinot que almacena usuarios registrados. Clave primaria: `user_id`. Soft delete con `deleted=FALSE/TRUE`. |
| **fact_wishlist** | Tabla REALTIME en Pinot que almacena items de la wishlist. Clave primaria: `wishlist_id` = `{user_id}_{game_slug}`. |
| **emp_records** | Tabla REALTIME en Pinot que almacena las 10 colecciones empresariales (empleados, contratos, etc.) en una estructura genérica (`record_id`, `collection`, `data_json`). |
| **fact_videogames** | Tabla OFFLINE en Pinot con ~1.7 M de videojuegos. Campos clave: `id`, `slug`, `name`, `rating`, `metacritic`, `genres`, `platforms`, `esrb_rating`, `semana`. |
| **semana** | Campo numérico (1-17) en `fact_videogames` que representa la semana de carga del catálogo OFFLINE. El slider del dashboard y los filtros de tienda usan `semana <= N`. |
| **Wishlist** | Lista de deseos del usuario registrado. Permite agregar, ver y eliminar juegos. El borrado usa tombstone Kafka. |
| **ESRB** | Entertainment Software Rating Board. Sistema de clasificación de videojuegos por edad (E, E10+, T, M, AO, RP). Almacenado en `esrb_rating` y en la dimensión `dim_esrb`. |
| **Metacritic** | Puntuación agregada de críticos especializados (0-100). Usada junto con `rating` para calcular el precio. |
| **RAWG API** | API externa de videojuegos (rawg.io) usada para enriquecer juegos con imágenes de fondo, screenshots y descripciones. Clave de API solo en backend. |
| **Precio** | Calculado con la fórmula: `max(1.99, rating*8 + metacritic*0.4)`. Si `rating=0` y `metacritic=0` → `0.00` (juego gratis). |
| **Juego gratis** | Juego cuyo `rating=0` y `metacritic=0`, resultando en `precio=0.00`. Filtrable con `price_filter=free`. |
| **authGuard** | Guard de Angular que protege rutas que requieren JWT válido. Redirige a login si no hay token. |
| **JWT** | JSON Web Token HS256 con expiración de 7 días. Transportado en el header `Authorization: Bearer <token>`. |
| **bcrypt** | Algoritmo de hash de contraseñas (passlib). Usado para almacenar contraseñas en `fact_users`. |
| **_esc()** | Función de escape que reemplaza comillas simples (`'`) y backslashes (`\`) en strings antes de insertarlos en queries Pinot. Previene SQL injection. |
| **slug** | Identificador URL-friendly único de un videojuego (ej.: `the-witcher-3-wild-hunt`). Usado en rutas de la tienda y como parte de la clave de wishlist. |
| **Tombstone** | Ver definición arriba. |
| **ETL** | Extract, Transform, Load. Pipeline que extrae datos de RAWG API, los transforma a Parquet y los carga a Pinot OFFLINE. Scripts `00`..`09` en `/etl/`. |
| **Docker Compose** | Orquestador local de contenedores. El stack de GameMetrics tiene 8 servicios en la red `gamemetrics` (172.20.0.0/16). |
| **inicio.ps1** | Script PowerShell de arranque del stack. Resuelve `NodeExistsException` de Zookeeper/Kafka en reinicios. |
| **DTOs Pydantic** | Data Transfer Objects definidos con Pydantic (BaseModel). Usados como `response_model` en cada endpoint FastAPI. |
| **dim_generos** | Dimensión OFFLINE de géneros de videojuegos. |
| **dim_plataformas** | Dimensión OFFLINE de plataformas (PC, PlayStation, Xbox, etc.). |
| **dim_desarrolladores** | Dimensión OFFLINE de estudios desarrolladores. |
| **dim_publicadores** | Dimensión OFFLINE de empresas publicadoras. |
| **dim_esrb** | Dimensión OFFLINE de clasificaciones ESRB. |
| **emp_records** | Ver definición arriba. Estructura genérica para las 10 colecciones empresariales. |
| **colección** | Namespace lógico dentro de `emp_records`. Valores válidos: `plataformas`, `generos`, `clasificaciones_esrb`, `desarrolladores`, `publicadores`, `empleados`, `contratos`, `catalogo_distribucion`, `campanas_marketing`, `evaluaciones_analiticas`. |
| **Stripe sandbox** | Entorno de pruebas del proveedor de pagos Stripe. [Planificado] para el paquete carrito. No requiere claves reales. |
| **Biblioteca** | [Planificado] Colección de juegos comprados por un usuario, visible en `/library`. |
| **Reseña verificada** | [Planificado] Reseña de un juego que solo puede escribir un usuario que lo haya comprado. |
| **Consistencia eventual** | Propiedad del sistema REALTIME: el dato escrito vía Kafka puede tardar hasta 2 segundos en ser visible en Pinot. La UI debe contemplar esta latencia. |
| **aiokafka** | Librería Python async usada como cliente Kafka en el backend FastAPI. |
| **OE1-OE4** | Objetivos estratégicos del sistema (ver `specs/000-sistema-general/spec.md`). |
| **RFC 2119** | Estándar que define las palabras clave de requisitos: MUST/SHALL (obligatorio), SHOULD (recomendado), MAY (opcional). |
