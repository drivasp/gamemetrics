# Plan Técnico — biblioteca [Planificado]

> Este plan describe el diseño a implementar. No existe código aún en el repositorio.

## Tabla Pinot REALTIME (creada por el paquete carrito)
**purchases**

| Campo | Tipo | Notas |
|-------|------|-------|
| `purchase_id` | STRING (PK) | UUID hex, generado en checkout |
| `user_id` | STRING | FK lógica a fact_users |
| `game_slug` | STRING | Juego comprado |
| `game_name` | STRING | Nombre en momento de compra |
| `game_image` | STRING | URL imagen |
| `amount` | FLOAT | Precio pagado |
| `purchased_at` | LONG | Epoch ms |
| `stripe_session_id` | STRING | Referencia de pago Stripe sandbox |

> La tabla `purchases` es creada y escrita por el paquete `carrito`. Este módulo solo la lee.

## Endpoints FastAPI a crear

| Método | Ruta | Auth | Archivo |
|--------|------|------|---------|
| GET | `/library` | JWT | `library/listar.py` |
| GET | `/library/check/{game_slug}` | JWT | `library/verificar.py` ⚠ primero en router |

## Módulo backend a crear

```
backend/library/
├── router.py       — APIRouter prefix="/library", tags=["library"]
├── listar.py       — GET /library (purchases WHERE user_id ORDER BY purchased_at DESC)
├── verificar.py    — GET /library/check/{game_slug} ({owned: bool})
└── modelos_library.py — LibraryItemDTO
```

## Registro en main.py
```python
from library.router import router as library_router
app.include_router(library_router)
```

## Flujo de lectura

```
GET /library
→ _require_token(authorization) → user_id
→ pinot_query("SELECT purchase_id, game_slug, game_name, game_image, amount, purchased_at
               FROM purchases WHERE user_id = '{_esc(user_id)}' ORDER BY purchased_at DESC LIMIT 500")
→ retorna list[LibraryItemDTO]

GET /library/check/{game_slug}
→ _require_token(authorization) → user_id
→ pinot_query("SELECT purchase_id FROM purchases
               WHERE user_id = '{user_id}' AND game_slug = '{slug}' LIMIT 1")
→ retorna {owned: len(rows) > 0}
```

## Componentes Angular a crear
- `LibraryComponent` — ruta `/library` protegida con `authGuard`; muestra cuadrícula de juegos comprados
- `LibraryService` — métodos: `getLibrary()`, `checkOwned(slug: string)`

## Integración con rutas Angular
```typescript
{ path: 'library', component: LibraryComponent, canActivate: [authGuard] },
```
