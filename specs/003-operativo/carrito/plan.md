# Plan Técnico — carrito [Planificado]

> Este plan describe el diseño a implementar. No existe código aún en el repositorio.

## Nuevas tablas Pinot REALTIME a crear

### fact_cart
| Campo | Tipo | Notas |
|-------|------|-------|
| `cart_item_id` | STRING (PK) | `{user_id}_{game_slug}` |
| `user_id` | STRING | FK lógica a fact_users |
| `game_slug` | STRING | Slug del juego |
| `game_name` | STRING | Nombre en momento de agregar |
| `game_image` | STRING | URL imagen |
| `game_price` | FLOAT | Precio fijo al agregar |
| `added_at` | LONG | Epoch ms |
| `deleted` | BOOLEAN | Tombstone para borrado lógico |

### purchases (también fuente para biblioteca)
| Campo | Tipo | Notas |
|-------|------|-------|
| `purchase_id` | STRING (PK) | UUID hex |
| `user_id` | STRING | Comprador |
| `game_slug` | STRING | Juego comprado |
| `game_name` | STRING | Nombre en momento de compra |
| `game_image` | STRING | URL imagen |
| `amount` | FLOAT | Precio pagado |
| `purchased_at` | LONG | Epoch ms |
| `stripe_session_id` | STRING | ID de sesión Stripe sandbox |

## Nuevos topics Kafka
- `fact_cart` — carrito (key: cart_item_id)
- `purchases` — compras confirmadas (key: purchase_id)

## Módulo backend a crear

```
backend/cart/
├── router.py        — APIRouter prefix="/cart", tags=["cart"]
├── agregar.py       — POST /cart/items
├── listar.py        — GET /cart
├── eliminar.py      — DELETE /cart/items/{slug}
├── vaciar.py        — DELETE /cart
├── checkout.py      — POST /cart/checkout (Stripe sandbox)
└── modelos_cart.py  — CartItemDTO, CartDTO, CheckoutResponseDTO
```

## Registro en main.py
```python
from cart.router import router as cart_router
app.include_router(cart_router)
```

## Flujo de checkout (P1)
```
POST /cart/checkout
→ _require_token() → user_id
→ GET /cart items de fact_cart para user_id
→ Stripe SDK sandbox: crear PaymentIntent o Session
→ Stripe confirma (sandbox: siempre exitoso)
→ para cada item: kafka_send("purchases", purchase_id, {...})
→ para cada item: kafka_send("fact_cart", cart_item_id, {..., deleted: True}) [tombstone]
→ retorna {status: "success", ...}
```

## Componentes Angular a crear
- `CartComponent` — ruta `/cart` protegida con `authGuard`
- `CheckoutComponent` — ruta `/checkout` protegida con `authGuard`
- `CartService` — métodos: `addToCart()`, `getCart()`, `removeFromCart()`, `clearCart()`, `checkout()`

## Integración con rutas Angular
```typescript
{ path: 'cart', component: CartComponent, canActivate: [authGuard] },
{ path: 'checkout', component: CheckoutComponent, canActivate: [authGuard] },
```
