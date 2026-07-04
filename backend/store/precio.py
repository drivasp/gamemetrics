from shared.cliente_pinot import pinot_query
from store.calcular_precio import calc_price


async def get_catalog_base_price(product_id: str, region: str = "US") -> float | None:
    rows = await pinot_query(
        f"SELECT base_price FROM fact_price_catalog "
        f"WHERE product_id = '{_esc(product_id)}' AND region_code = '{_esc(region)}' "
        f"ORDER BY semana DESC LIMIT 1"
    )
    if not rows:
        return None
    return float(rows[0][0])


async def get_active_discount_pct(product_id: str) -> float:
    now_ms = int(__import__("time").time() * 1000)
    rows = await pinot_query(
        f"SELECT discount_pct FROM fact_promotions "
        f"WHERE active = true AND deleted = false "
        f"AND start_at <= {now_ms} AND end_at >= {now_ms} "
        f"AND (product_id = '{_esc(product_id)}' OR product_id = '*') "
        f"ORDER BY discount_pct DESC LIMIT 1"
    )
    if not rows:
        return 0.0
    return float(rows[0][0])


def _esc(s: str) -> str:
    return s.replace("'", "''").replace("\\", "\\\\")


async def resolve_price(
    product_id: str,
    rating: float,
    metacritic: float,
    region: str = "US",
) -> tuple[float, float, float]:
    """Retorna (precio_final, precio_base, descuento_pct)."""
    catalog = await get_catalog_base_price(product_id, region)
    base = catalog if catalog is not None else calc_price(rating, metacritic)
    discount = await get_active_discount_pct(product_id)
    if base == 0.0:
        return 0.0, 0.0, 0.0
    final = round(base * (1 - discount / 100.0), 2)
    return final, base, discount
