# Plan Técnico — auth [Implementado]

## Tabla Pinot REALTIME
**fact_users**
| Campo | Tipo | Notas |
|-------|------|-------|
| `user_id` | STRING (PK) | UUID hex generado en servidor |
| `email` | STRING | Único, filtrado con `deleted = FALSE` |
| `password_hash` | STRING | bcrypt; nunca en respuestas |
| `display_name` | STRING | Opcional, cadena vacía si no se provee |
| `bio` | STRING | Opcional, cadena vacía por defecto |
| `avatar` | STRING | URL relativa `/static/avatars/{user_id}.{ext}` |
| `deleted` | BOOLEAN | Tombstone para borrado lógico |
| `created_at` | LONG | Epoch ms |

## Topic Kafka
- **Nombre:** `fact_users`
- **Clave:** `user_id`
- **Upsert:** sí (clave primaria en Pinot REALTIME)

## Endpoints FastAPI

| Método | Ruta | Archivo | Auth |
|--------|------|---------|------|
| POST | `/auth/register` | `auth/registro.py` | No |
| POST | `/auth/login` | `auth/login.py` | No |
| GET | `/auth/profile` | `auth/perfil.py` | JWT Bearer |
| PUT | `/auth/profile` | `auth/perfil.py` | JWT Bearer |
| POST | `/auth/avatar` | `auth/avatar.py` | JWT Bearer |

## Módulos del paquete

```
backend/auth/
├── router.py         — agrega los 4 sub-routers con prefix="/auth"
├── registro.py       — POST /register
├── login.py          — POST /login
├── perfil.py         — GET/PUT /profile
├── avatar.py         — POST /avatar
├── modelos_auth.py   — RegisterDTO, LoginDTO, UserDTO, AuthResponseDTO, UpdateProfileDTO
└── cliente_jwt.py    — hash_password, verify_password, create_token, verify_token, new_id
```

## Componentes Angular

| Componente | Ruta | Guard |
|------------|------|-------|
| `ProfileComponent` | `/profile` | `authGuard` |
| `LoginComponent` (modal/inline) | — | No |
| `RegisterComponent` (modal/inline) | — | No |

## Servicio Angular
- `AuthService` — métodos: `register()`, `login()`, `getProfile()`, `updateProfile()`, `uploadAvatar()`, `logout()`, `isLoggedIn()`.

## Flujo de escritura (P1, C4)
```
POST /auth/register
→ pinot_query("SELECT user_id FROM fact_users WHERE email='...' AND deleted=FALSE LIMIT 1")
→ si existe → HTTP 400
→ si no existe → new_id() + hash_password()
→ kafka_send("fact_users", user_id, {todos los campos, deleted:false})
→ create_token(user_id, email) → retorna {token, user}
```

## Archivos estáticos
- Avatares: `/app/static/avatars/` (montado en Docker, servido en `/static/`)
- URL en Pinot: `/static/avatars/{user_id}.{ext}`
