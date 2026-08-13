"""
RBAC profesional GameMetrics.

Roles canónicos (compatibles con player/publisher/admin legacy):
  player, developer, publisher, partner, moderator, support, finance, admin, super_admin

Permisos (scopes) granulares — la autorización REAL está en backend.
"""
from __future__ import annotations

# Legacy aliases map into canonical set
ROLE_ALIASES = {
    "user": "player",
    "ops": "admin",
}

ROLES = frozenset({
    "player",
    "developer",
    "publisher",
    "partner",
    "moderator",
    "support",
    "finance",
    "admin",
    "super_admin",
})

DEFAULT_ROLE = "player"

# permission -> roles that grant it
PERMISSIONS: dict[str, frozenset[str]] = {
    "store.read": frozenset(ROLES),
    "library.read": frozenset(ROLES),
    "wallet.use": frozenset({"player", "developer", "publisher", "partner", "admin", "super_admin"}),
    "checkout.buy": frozenset({"player", "developer", "publisher", "partner", "admin", "super_admin"}),
    "partner.manage": frozenset({"publisher", "partner", "developer", "admin", "super_admin"}),
    "partner.own_only": frozenset({"publisher", "partner", "developer", "admin", "super_admin"}),
    "reports.read": frozenset({"finance", "admin", "super_admin"}),
    "reports.export": frozenset({"finance", "admin", "super_admin"}),
    "finance.audit": frozenset({"finance", "admin", "super_admin"}),
    "finance.payout": frozenset({"finance", "admin", "super_admin"}),
    "admin.users": frozenset({"admin", "super_admin"}),
    "admin.claims": frozenset({"admin", "super_admin"}),
    "moderation.act": frozenset({"moderator", "admin", "super_admin"}),
    "support.tickets": frozenset({"support", "moderator", "admin", "super_admin"}),
    "empresa.write": frozenset({"admin", "super_admin"}),
    "empresa.read": frozenset({"admin", "super_admin", "finance"}),
    "ops.dashboard": frozenset({"admin", "super_admin"}),
}


def normalize_role(role: str | None) -> str:
    r = (role or DEFAULT_ROLE).strip().lower()
    r = ROLE_ALIASES.get(r, r)
    return r if r in ROLES else DEFAULT_ROLE


def role_has_permission(role: str, permission: str) -> bool:
    role = normalize_role(role)
    allowed = PERMISSIONS.get(permission)
    if not allowed:
        return False
    if role == "super_admin":
        return True
    return role in allowed


def permissions_for_role(role: str) -> list[str]:
    role = normalize_role(role)
    if role == "super_admin":
        return sorted(PERMISSIONS.keys())
    return sorted(p for p, roles in PERMISSIONS.items() if role in roles)
