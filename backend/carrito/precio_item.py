from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from tienda.precio import resolve_price


async def resolve_item_price(product_id: str, game_slug: str) -> tuple[float, float, float]:
    """Retorna (precio_final, precio_base, descuento_pct) para un ítem del carrito."""
    rows = await pinot_query(
        f"SELECT rating, metacritic FROM fact_videogames "
        f"WHERE slug = '{esc(game_slug)}' AND semana = 1 LIMIT 1"
    )
    if not rows:
        rows = await pinot_query(
            f"SELECT rating, metacritic FROM fact_videogames "
            f"WHERE id = '{esc(product_id)}' AND semana = 1 LIMIT 1"
        )
    rating = float(rows[0][0] or 0) if rows else 0.0
    metacritic = float(rows[0][1] or 0) if rows else 0.0
    return await resolve_price(product_id, rating, metacritic)
