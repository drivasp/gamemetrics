"""
Modelo de producto tipado (referencia Steamworks DLC docs).

Tipos: game | dlc | demo | edition | bundle | build_meta

NO IMPLEMENTA todavía el catálogo completo DLC/bundles en store/checkout.
Este módulo define contratos y validación para evitar un segundo sistema financiero.
"""
from __future__ import annotations

from typing import Literal

ProductType = Literal["game", "dlc", "demo", "edition", "bundle", "build"]

VALID_PRODUCT_TYPES = frozenset(
    {"game", "dlc", "demo", "edition", "bundle", "build"}
)


def normalize_product_type(value: str | None) -> str:
    v = (value or "game").strip().lower()
    return v if v in VALID_PRODUCT_TYPES else "game"


def requires_parent_app(product_type: str) -> bool:
    return normalize_product_type(product_type) in {"dlc", "edition", "demo"}


def is_purchasable(product_type: str) -> bool:
    return normalize_product_type(product_type) != "build"
