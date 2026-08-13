# Fase 0 — Roles (player / publisher / admin)

## Objetivo

Un solo login. El token/perfil lleva un **rol** que controla qué puede hacer cada cuenta.

| Rol | Quién | Puede |
|-----|--------|--------|
| `player` | Jugador (default al registrarse) | Tienda, carrito, biblioteca, social |
| `publisher` | Estudio (al registrarse como partner) | `/partners/*`, panel publisher |
| `admin` | GameMetrics (bootstrap / promoción) | `/admin/*`, promover roles |

## Persistencia

Tabla Pinot REALTIME `fact_user_roles` (no altera `fact_users` para no romper datos).

Campos: `user_id`, `role`, `updated_at`, `deleted`.

Cache en memoria del backend para mitigar lag Pinot.

## APIs

- Registro → crea rol `player`
- Login / perfil → incluyen `role`
- `POST /partners/register` → asigna `publisher` (+ guards en mutaciones partner)
- `POST /auth/bootstrap-admin` `{ email, password, display_name?, secret }` → crea/promueve **admin**
  - Secret: env `ROLE_BOOTSTRAP_SECRET` (default dev)
- `GET /admin/health` → solo `admin`
- `PUT /admin/users/{user_id}/role` `{ role }` → solo `admin`

## JWT

Claim `role` en el token. Se renueva en login / cambio de rol.

## Separación de experiencias

| Quién | Ve |
|-------|-----|
| **player / publisher** | Solo tienda (Steam-like): TIENDA, BIBLIOTECA, etc. |
| **admin** | Dashboard ETL, Empresa, Dimensiones + Admin + Tienda |

Rutas `/`, `/empresa`, `/dimensiones` protegidas con `opsGuard` (solo admin).

## Setup tablas

```bash
docker compose exec etl-api python 19_create_user_roles_table.py
```
