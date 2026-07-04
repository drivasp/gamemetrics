# Checklist de Validación — auth [Implementado]

## Seguridad (Q1, Q2)
- [ ] Las contraseñas se hashean con bcrypt antes de enviarse a Kafka
- [ ] Ningún endpoint retorna `password_hash` en el JSON de respuesta
- [ ] Todos los endpoints protegidos validan JWT Bearer antes de operar
- [ ] El mensaje de error de login es genérico (no revela si el email existe)
- [ ] `_esc()` aplicado a email en queries Pinot de registro y login

## Flujo Kafka (P1, C4)
- [ ] `POST /auth/register` llama a `kafka_send("fact_users", user_id, {...})`
- [ ] `PUT /auth/profile` llama a `kafka_send("fact_users", user_id, {...})` con payload completo
- [ ] `POST /auth/avatar` llama a `kafka_send("fact_users", user_id, {...})` con avatar URL
- [ ] Ningún endpoint escribe directamente a Pinot

## Consistencia eventual (P4)
- [ ] `GET /auth/profile` maneja condición de carrera: retorna datos del JWT si Pinot no tiene el registro aún

## Funcionalidad
- [ ] `POST /auth/register` retorna HTTP 200 con token y UserDTO
- [ ] `POST /auth/register` retorna HTTP 400 si email duplicado
- [ ] `POST /auth/login` retorna HTTP 200 con token de 7 días
- [ ] `POST /auth/login` retorna HTTP 400 con mensaje genérico si falla
- [ ] `GET /auth/profile` sin token retorna HTTP 401
- [ ] `PUT /auth/profile` actualiza solo campos enviados (merge parcial)
- [ ] `POST /auth/avatar` guarda archivo en `/app/static/avatars/` y actualiza campo avatar

## Código (C1, C5)
- [ ] Cada endpoint tiene `response_model` explícito (Pydantic DTO)
- [ ] `router.py` agrega los 4 sub-routers con prefijo `/auth`
- [ ] `auth_router` registrado en `backend/main.py`
- [ ] Archivos estáticos montados en FastAPI: `app.mount("/static", StaticFiles(...))`

## Frontend (C6)
- [ ] `ProfileComponent` protegido con `authGuard`
- [ ] `AuthService` implementado con métodos para todos los endpoints
- [ ] Ruta `/profile` en `app.routes.ts` con `canActivate: [authGuard]`
