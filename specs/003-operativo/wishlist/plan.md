# Plan Técnico — wishlist [Implementado]

## Tabla Pinot REALTIME
**fact_wishlist**

| Campo | Tipo | Notas |
|-------|------|-------|
| `wishlist_id` | STRING (PK) | `{user_id}_{game_slug}` |
| `user_id` | STRING | FK lógica a fact_users |
| `game_slug` | STRING | Slug del juego |
| `game_name` | STRING | Nombre en el momento de agregar |
| `game_image` | STRING | URL de imagen (puede ser vacío) |
| `game_price` | FLOAT | Precio calculado en el momento de agregar |
| `created_at` | LONG | Epoch ms |
| `deleted` | BOOLEAN | Tombstone para borrado lógico |

## Topic Kafka
- **Nombre:** `fact_wishlist`
- **Clave:** `wishlist_id` = `{user_id}_{game_slug}`
- **Upsert:** sí (deleteRecordColumn configurado para tombstone)

## Endpoints FastAPI

| Método | Ruta | Auth | Archivo |
|--------|------|------|---------|
| GET | `/user/wishlist/check/{game_slug}` | JWT | `user/wishlist.py` ⚠ primero |
| GET | `/user/wishlist` | JWT | `user/wishlist.py` |
| POST | `/user/wishlist` | JWT | `user/wishlist.py` |
| DELETE | `/user/wishlist/{game_slug}` | JWT | `user/wishlist.py` |

## Estructura del módulo

```
backend/user/
├── router.py        — agrega wishlist_router con prefijo "/user"
├── wishlist.py      — todos los endpoints de wishlist
└── modelos_user.py  — WishlistItemDTO, AddWishlistDTO
```

## Flujo de escritura — Agregar (P1, C4, P2)

```
POST /user/wishlist
→ _require_token(authorization) → user_id
→ wid = f"{user_id}_{body.game_slug}"
→ pinot_query("SELECT wishlist_id FROM fact_wishlist WHERE wishlist_id = '...' LIMIT 1")
→ si existe → HTTP 409
→ kafka_send("fact_wishlist", wid, {wishlist_id, user_id, game_slug, game_name, game_image, game_price, created_at})
→ retorna WishlistItemDTO (HTTP 201)
```

## Flujo de borrado — Tombstone (P2)

```
DELETE /user/wishlist/{game_slug}
→ _require_token(authorization) → user_id
→ wid = f"{user_id}_{game_slug}"
→ pinot_query("SELECT wishlist_id FROM fact_wishlist WHERE wishlist_id = '...' LIMIT 1")
→ si no existe → HTTP 404
→ kafka_send("fact_wishlist", wid, {wishlist_id, user_id, game_slug, game_name: "", game_image: "", game_price: 0.0, deleted: True, created_at: now_ms})
→ Pinot usa deleteRecordColumn para eliminar el registro
→ retorna HTTP 204
```

## Componentes Angular
- `WishlistComponent` — lista de items con botón de eliminar
- Botón "Agregar a Wishlist" en `StoreGameDetailComponent` (usa `authGuard` implícito: muestra login si no hay token)

## Servicio Angular
- `WishlistService` — métodos: `getWishlist()`, `addToWishlist(item)`, `removeFromWishlist(slug)`, `checkWishlist(slug)`.
