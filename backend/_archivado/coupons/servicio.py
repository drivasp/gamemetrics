"""Cupones y redenciones — estilo Steam."""
from __future__ import annotations

import time
import uuid

from shared.auth_deps import esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool, to_ms


class CouponResult:
    def __init__(
        self,
        code: str,
        discount_type: str,
        discount_value: float,
        discount_applied: float,
        max_uses: int,
        uses_count: int,
        valid_from: int,
        valid_until: int,
    ):
        self.code = code
        self.discount_type = discount_type
        self.discount_value = discount_value
        self.discount_applied = discount_applied
        self.max_uses = max_uses
        self.uses_count = uses_count
        self.valid_from = valid_from
        self.valid_until = valid_until


async def validate_coupon(code: str, subtotal: float, user_id: str | None = None) -> CouponResult:
    safe = esc(code.strip().upper())
    rows = await pinot_query(
        f"SELECT coupon_code, discount_type, discount_value, max_uses, uses_count, "
        f"valid_from, valid_until, deleted FROM fact_coupons "
        f"WHERE coupon_code = '{safe}' LIMIT 1"
    )
    if not rows or to_bool(rows[0][7]):
        raise ValueError("Cupón no válido")

    code_v, dtype, dval, max_uses, uses_count, valid_from, valid_until, _ = rows[0]
    now_ms = int(time.time() * 1000)
    vf = to_ms(valid_from)
    vu = int(valid_until or 0)
    if vf and now_ms < vf:
        raise ValueError("Este cupón aún no está activo")
    if vu and now_ms > vu:
        raise ValueError("Este cupón ha expirado")
    max_u = int(max_uses or 0)
    used = int(uses_count or 0)
    if max_u > 0 and used >= max_u:
        raise ValueError("Este cupón ya alcanzó el máximo de usos")

    if user_id:
        prior = await pinot_query(
            f"SELECT redemption_id FROM fact_coupon_redemptions "
            f"WHERE user_id = '{esc(user_id)}' AND coupon_code = '{safe}' "
            f"AND deleted = false LIMIT 1"
        )
        if prior:
            raise ValueError("Ya usaste este cupón")

    dtype_s = str(dtype or "pct").lower()
    dval_f = float(dval or 0)
    sub = max(0.0, float(subtotal))
    if dtype_s == "fixed":
        applied = min(dval_f, sub)
    else:
        applied = round(sub * (dval_f / 100.0), 2)
        applied = min(applied, sub)

    if applied <= 0:
        raise ValueError("El cupón no aplica a este carrito")

    return CouponResult(
        code=str(code_v).upper(),
        discount_type=dtype_s,
        discount_value=dval_f,
        discount_applied=round(applied, 2),
        max_uses=max_u,
        uses_count=used,
        valid_from=vf,
        valid_until=vu,
    )


async def redeem_coupon(
    code: str,
    user_id: str,
    order_id: str,
    discount_applied: float,
    uses_count: int,
    discount_type: str,
    discount_value: float,
    max_uses: int,
    valid_from: int,
    valid_until: int,
) -> str:
    now_ms = int(time.time() * 1000)
    rid = uuid.uuid4().hex[:15]
    safe = code.upper()

    await kafka_send("fact_coupon_redemptions", rid, {
        "redemption_id": rid,
        "coupon_code": safe,
        "user_id": user_id,
        "order_id": order_id,
        "discount_applied": round(discount_applied, 2),
        "created_at": now_ms,
        "deleted": False,
    })

    await kafka_send("fact_coupons", safe, {
        "coupon_code": safe,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "max_uses": max_uses,
        "uses_count": uses_count + 1,
        "valid_from": valid_from or now_ms,
        "valid_until": valid_until or 0,
        "deleted": False,
    })
    return rid
