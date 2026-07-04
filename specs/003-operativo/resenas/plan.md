# Plan Técnico — resenas [Planificado]

> Este plan describe el diseño a implementar. No existe código aún en el repositorio.

## Nueva tabla Pinot REALTIME a crear

### reviews
| Campo | Tipo | Notas |
|-------|------|-------|
| `review_id` | STRING (PK) | `{user_id}_{game_slug}` |
| `user_id` | STRING | FK lógica a fact_users |
| `game_slug` | STRING | Juego reseñado |
| `rating` | INT | 1-5 estrellas |
| `comment` | STRING | Texto de la reseña (máx. 2000 chars) |
| `created_at` | LONG | Epoch ms |
| `updated_at` | LONG | Epoch ms (para ediciones) |
| `deleted` | BOOLEAN | Tombstone para borrado lógico |

## Nuevo topic Kafka
- `reviews` — reseñas (key: review_id = `{user_id}_{game_slug}`)
- Upsert por `review_id` + `deleteRecordColumn` para tombstone

## Módulo backend a crear

```
backend/reviews/
├── router.py       — APIRouter prefix="/reviews", tags=["reviews"]
├── crear.py        — POST /reviews/{game_slug} (verificar compra + kafka_send)
├── listar.py       — GET /reviews/{game_slug} (público, avg_rating, total)
├── editar.py       — PUT /reviews/{game_slug} (solo autor, kafka_send)
├── eliminar.py     — DELETE /reviews/{game_slug} (solo autor, tombstone)
└── modelos_reviews.py — ReviewDTO, ReviewPageDTO, CreateReviewDTO, UpdateReviewDTO
```

## Registro en main.py
```python
from reviews.router import router as reviews_router
app.include_router(reviews_router)
```

## Flujo de verificación de compra (P1)

```
POST /reviews/{game_slug}
→ _require_token(authorization) → user_id
→ pinot_query("SELECT purchase_id FROM purchases
               WHERE user_id = '{user_id}' AND game_slug = '{slug}' LIMIT 1")
→ si no existe → HTTP 403 "Debes comprar el juego para poder reseñarlo"
→ review_id = f"{user_id}_{game_slug}"
→ pinot_query("SELECT review_id FROM reviews WHERE review_id = '{review_id}' AND deleted = FALSE LIMIT 1")
→ si existe → HTTP 409 "Ya tienes una reseña de este juego"
→ kafka_send("reviews", review_id, { ..., rating, comment, deleted: false })
→ retorna ReviewDTO (HTTP 201)
```

## Flujo de lectura pública

```
GET /reviews/{game_slug}
→ (sin JWT requerido)
→ pinot_query("SELECT review_id, user_id, rating, comment, created_at
               FROM reviews WHERE game_slug = '{slug}' AND deleted = FALSE
               ORDER BY created_at DESC LIMIT 100")
→ pinot_query("SELECT AVG(rating), COUNT(*) FROM reviews
               WHERE game_slug = '{slug}' AND deleted = FALSE")
→ retorna ReviewPageDTO {reviews, avg_rating, total}
```

## Componentes Angular a crear
- `ReviewsComponent` — listado de reseñas embebido en `StoreGameDetailComponent`
- `WriteReviewComponent` — formulario de reseña (visible solo si usuario tiene JWT Y posee el juego)
- `ReviewsService` — métodos: `getReviews(slug)`, `createReview(slug, data)`, `updateReview(slug, data)`, `deleteReview(slug)`

## Integración con app.routes.ts
Las reseñas se muestran dentro de la página de detalle del juego; no tienen ruta propia.
