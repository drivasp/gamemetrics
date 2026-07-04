# Paquete auth — Autenticación y Gestión de Cuenta [Implementado]

## 1. Nombre del paquete
**auth** — Registro, Login, Perfil y Avatar de Usuario

## 2. Objetivo
Gestionar el ciclo de vida de la cuenta del usuario: registro con email/contraseña, autenticación por JWT, consulta y edición del perfil, y carga de avatar. Toda escritura de datos de usuario pasa por Kafka → Pinot REALTIME (`fact_users`).

## 3. Contexto
GameMetrics S.A. necesita identificar a sus usuarios para proteger las funcionalidades transaccionales (wishlist, futuro carrito). El sistema usa JWT HS256 con expiración de 7 días y bcrypt para el hash de contraseñas. La tabla `fact_users` en Pinot REALTIME actúa como única fuente de verdad de usuarios, con borrado lógico mediante tombstone.

## 4. Ubicación
- **Nivel empresarial:** Operativo (003)
- **Departamento:** Cuentas y Acceso
- **Paquete:** auth

## 5. Actores

| Actor | Rol |
|-------|-----|
| Visitante | Puede registrarse y hacer login. |
| Usuario Registrado | Puede ver y editar su perfil y subir avatar. |
| Sistema (Kafka producer) | Persiste eventos de creación/actualización de usuario. |

## 6. Casos de uso

| Código | Nombre | Actor | OE relacionado |
|--------|--------|-------|----------------|
| CU-O01 | Registrar nuevo usuario | Visitante | OE2 |
| CU-O02 | Iniciar sesión (login) | Visitante | OE2 |
| CU-O03-a | Ver perfil propio | Usuario Registrado | OE2 |
| CU-O08 | Editar perfil (display_name, bio) | Usuario Registrado | OE2 |
| CU-O08-b | Subir avatar de perfil | Usuario Registrado | OE2 |

## 7. Historias de usuario

| Código | Historia |
|--------|----------|
| US-AUTH-001 | Como Visitante, quiero registrarme con email y contraseña para acceder a las funcionalidades exclusivas de usuarios. |
| US-AUTH-002 | Como Visitante, quiero iniciar sesión con mis credenciales para obtener un token JWT y acceder a mi cuenta. |
| US-AUTH-003 | Como Usuario Registrado, quiero ver mi perfil (email, nombre, bio, avatar) para verificar mis datos. |
| US-AUTH-004 | Como Usuario Registrado, quiero editar mi nombre de usuario y bio para personalizar mi perfil. |
| US-AUTH-005 | Como Usuario Registrado, quiero subir una imagen de avatar para personalizar mi presencia en la plataforma. |
| US-AUTH-006 | Como Usuario Registrado, quiero que mi sesión dure 7 días sin necesidad de volver a iniciar sesión. |

## 8. Requisitos funcionales

| Código | Requisito |
|--------|-----------|
| RF-AUTH-001 | El sistema MUST proveer `POST /auth/register` que acepte `{email, password, display_name?}` y retorne `{token, user}`. |
| RF-AUTH-002 | El sistema MUST verificar que el email no existe en `fact_users` antes de crear el usuario; si existe, MUST retornar HTTP 400. |
| RF-AUTH-003 | El sistema MUST persistir el nuevo usuario enviando un evento a Kafka topic `fact_users` con `kafka_send(topic, user_id, payload)`. |
| RF-AUTH-004 | El sistema MUST proveer `POST /auth/login` que acepte `{email, password}`, verifique bcrypt y retorne `{token, user}`. |
| RF-AUTH-005 | El sistema MUST retornar HTTP 400 con mensaje genérico "Email o contraseña incorrectos" tanto si el email no existe como si la contraseña es incorrecta (no revelar cuál falló). |
| RF-AUTH-006 | El sistema MUST proveer `GET /auth/profile` protegido por JWT Bearer que retorne los datos del usuario autenticado. |
| RF-AUTH-007 | El sistema MUST proveer `PUT /auth/profile` protegido por JWT Bearer que acepte `{display_name?, bio?}` y actualice el perfil vía Kafka. |
| RF-AUTH-008 | El sistema MUST proveer `POST /auth/avatar` protegido por JWT Bearer que acepte un archivo `multipart/form-data`, lo almacene en `/app/static/avatars/{user_id}.{ext}` y actualice el campo `avatar` en `fact_users` vía Kafka. |
| RF-AUTH-009 | El token JWT MUST tener expiración de 7 días y algoritmo HS256. El payload MUST incluir `id` (user_id) y `email`. |
| RF-AUTH-010 | Las contraseñas MUST hashearse con bcrypt antes de almacenarse. Nunca se guarda texto plano. |
| RF-AUTH-011 | El `user_id` MUST generarse en el servidor (UUID v4 hex). El cliente no puede asignarlo. |
| RF-AUTH-012 | El sistema MUST manejar la condición de carrera entre registro y visibilidad en Pinot: si el perfil no está aún indexado, `GET /auth/profile` MUST retornar los datos del payload JWT. |

## 9. Requisitos no funcionales

| Código | Requisito |
|--------|-----------|
| RNF-AUTH-001 | El login MUST completarse en < 1 segundo (bcrypt + consulta Pinot). |
| RNF-AUTH-002 | El avatar subido MUST almacenarse localmente en el contenedor FastAPI; el campo `avatar` en Pinot almacena la URL relativa `/static/avatars/{filename}`. |
| RNF-AUTH-003 | Los errores de autenticación MUST retornar HTTP 401 con mensaje sin revelar detalles internos. |
| RNF-AUTH-004 | El sistema SHOULD contemplar la latencia eventual (< 2 s) entre el registro y la visibilidad del usuario en Pinot REALTIME. |

## 10. Reglas de negocio

| Código | Regla |
|--------|-------|
| RN-AUTH-001 | Un email solo puede usarse una vez; la unicidad se verifica en `fact_users` con `deleted = FALSE`. |
| RN-AUTH-002 | El borrado de usuarios es lógico (tombstone `deleted=TRUE`); no se eliminan registros de Pinot. |
| RN-AUTH-003 | Los campos `display_name` y `bio` son opcionales; pueden ser cadena vacía pero no nulos en Kafka. |
| RN-AUTH-004 | La actualización del perfil (PUT) envía el registro completo a Kafka (upsert idempotente), preservando `password_hash` y `email`. |
| RN-AUTH-005 | El avatar previo es sobreescrito en disco al subir uno nuevo; solo se conserva el último. |

## 11. Entradas y salidas

### POST /auth/register
| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Entrada** `email` | string | Email único del usuario |
| **Entrada** `password` | string | Contraseña en texto plano (se hashea en backend) |
| **Entrada** `display_name` | string? | Nombre de visualización (opcional) |
| **Salida** `token` | string | JWT HS256 con 7 días de expiración |
| **Salida** `user` | UserDTO | `{id, email, display_name, bio, avatar}` |

### POST /auth/login
| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Entrada** `email` | string | Email registrado |
| **Entrada** `password` | string | Contraseña en texto plano |
| **Salida** `token` | string | JWT HS256 |
| **Salida** `user` | UserDTO | Datos del usuario autenticado |

### GET /auth/profile
| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Header** `Authorization` | string | `Bearer <token>` |
| **Salida** | UserDTO | `{id, email, display_name, bio, avatar}` |

### PUT /auth/profile
| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Header** `Authorization` | string | `Bearer <token>` |
| **Entrada** `display_name` | string? | Nuevo nombre (opcional) |
| **Entrada** `bio` | string? | Nueva bio (opcional) |
| **Salida** | UserDTO | Perfil actualizado |

### POST /auth/avatar
| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Header** `Authorization` | string | `Bearer <token>` |
| **Entrada** `file` | UploadFile | Imagen en multipart/form-data |
| **Salida** | UserDTO | Perfil con URL de avatar actualizada |

## 12. Escenarios Gherkin

**Escenario exitoso: Registro de usuario**
```gherkin
Dado que un Visitante envía POST /auth/register con email "ana@test.com" y password "Segura123"
Y el email no existe en fact_users
Cuando el backend procesa la solicitud
Entonces genera un user_id único (UUID hex)
Y hashea la contraseña con bcrypt
Y envía kafka_send("fact_users", user_id, {email, password_hash, deleted: false, ...})
Y retorna HTTP 200 con {token: "<JWT>", user: {id, email, display_name: null}}
Y el usuario aparece en fact_users en Pinot en menos de 2 segundos
```

**Escenario de error: Email duplicado**
```gherkin
Dado que el email "ana@test.com" ya existe en fact_users con deleted=FALSE
Cuando el Visitante envía POST /auth/register con el mismo email
Entonces el backend retorna HTTP 400 con mensaje "Este email ya está en uso"
Y NO se envía ningún evento a Kafka
```

**Escenario exitoso: Login**
```gherkin
Dado que el usuario "ana@test.com" existe en fact_users con deleted=FALSE
Y envía POST /auth/login con password correcto
Cuando el backend verifica bcrypt
Entonces retorna HTTP 200 con {token: "<JWT válido 7 días>", user: {...}}
```

**Escenario de error: Contraseña incorrecta**
```gherkin
Dado que el usuario "ana@test.com" existe
Y envía POST /auth/login con password incorrecto
Cuando el backend verifica bcrypt
Entonces retorna HTTP 400 con "Email o contraseña incorrectos" (mensaje genérico)
```

**Escenario exitoso: Editar perfil**
```gherkin
Dado que el Usuario Registrado tiene token JWT válido
Y envía PUT /auth/profile con {display_name: "Anita", bio: "Gamer"}
Cuando el backend valida el token y obtiene el usuario de Pinot
Entonces envía kafka_send con el registro completo actualizado
Y retorna HTTP 200 con el UserDTO actualizado
```

**Escenario: Condición de carrera post-registro**
```gherkin
Dado que el usuario acaba de registrarse hace menos de 2 segundos
Y el registro aún no está indexado en Pinot REALTIME
Cuando llama a GET /auth/profile con su token
Entonces el backend retorna los datos del payload JWT (id, email) en lugar de HTTP 404
```

## 13. Criterios de aceptación

| Código | Criterio |
|--------|----------|
| CA-AUTH-001 | POST /auth/register con email nuevo retorna HTTP 200 con token JWT y UserDTO. |
| CA-AUTH-002 | POST /auth/register con email duplicado retorna HTTP 400. |
| CA-AUTH-003 | POST /auth/login con credenciales correctas retorna HTTP 200 con token válido. |
| CA-AUTH-004 | POST /auth/login con contraseña incorrecta retorna HTTP 400 con mensaje genérico. |
| CA-AUTH-005 | GET /auth/profile sin token retorna HTTP 401. |
| CA-AUTH-006 | PUT /auth/profile con token válido actualiza display_name y bio en Pinot en < 2 s. |
| CA-AUTH-007 | POST /auth/avatar guarda el archivo en `/app/static/avatars/` y actualiza el campo `avatar` en fact_users. |
| CA-AUTH-008 | El token generado decodifica correctamente con `user_id` y `email` en el payload. |
| CA-AUTH-009 | La contraseña nunca aparece en texto plano en ninguna respuesta ni log. |

## 14. Dependencias

| Paquete | Tipo |
|---------|------|
| `shared/kafka_producer.py` | `kafka_send()` para escrituras a `fact_users` |
| `shared/cliente_pinot.py` | Lectura de `fact_users` |
| `auth/cliente_jwt.py` | `hash_password()`, `verify_password()`, `create_token()`, `verify_token()`, `new_id()` |
| topic Kafka `fact_users` | Destino de escritura; Pinot REALTIME lo consume |
| `wishlist` (003-operativo) | Depende de auth para validar JWT en sus endpoints |

## 15. Fuera de alcance

- Recuperación de contraseña vía email (planificado).
- Autenticación con proveedores OAuth (Google, Steam) — planificado.
- Verificación de email en el registro.
- Cierre de sesión activo (revocación de JWT) — el token simplemente expira.
- Roles y permisos granulares (RBAC).
