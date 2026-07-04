# Tareas — auth [Implementado]

- [x] T-AUTH-01: Implementar `auth/cliente_jwt.py` con `hash_password`, `verify_password`, `create_token` (HS256 7d), `verify_token`, `new_id`
- [x] T-AUTH-02: Implementar `auth/modelos_auth.py` con `RegisterDTO`, `LoginDTO`, `UserDTO`, `AuthResponseDTO`, `UpdateProfileDTO`
- [x] T-AUTH-03: Implementar `auth/registro.py` — POST /auth/register con verificación de email duplicado y kafka_send
- [x] T-AUTH-04: Implementar `auth/login.py` — POST /auth/login con verificación bcrypt y retorno de token
- [x] T-AUTH-05: Implementar `auth/perfil.py` — GET/PUT /auth/profile con validación JWT y kafka_send en PUT
- [x] T-AUTH-06: Implementar `auth/avatar.py` — POST /auth/avatar con almacenamiento de archivo y kafka_send
- [x] T-AUTH-07: Implementar `auth/router.py` incluyendo los 4 sub-routers con prefijo `/auth`
- [x] T-AUTH-08: Registrar `auth_router` en `backend/main.py`
- [x] T-AUTH-09: Implementar `_require_token()` helper en `perfil.py` y `avatar.py` para validación JWT
- [x] T-AUTH-010: Implementar `ProfileComponent` en Angular con ruta `/profile` protegida por `authGuard`
- [x] T-AUTH-011: Implementar `AuthService` en Angular con métodos de login, register y perfil
- [x] T-AUTH-012: Montar directorio de estáticos `/app/static` en FastAPI con `StaticFiles`
- [ ] T-AUTH-013: Agregar validación de formato de email (regex) en `RegisterDTO`
- [ ] T-AUTH-014: Agregar validación de longitud mínima de contraseña (mín. 8 caracteres) en `RegisterDTO`
- [ ] T-AUTH-015: Implementar recuperación de contraseña por email
