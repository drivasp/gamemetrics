"""Unit tests RBAC permissions + normalize_role (sin Docker)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.permissions import (  # noqa: E402
    ROLES,
    normalize_role,
    permissions_for_role,
    role_has_permission,
)


def test_roles_include_requested():
    for r in (
        "player", "developer", "publisher", "partner",
        "moderator", "support", "finance", "admin", "super_admin",
    ):
        assert r in ROLES


def test_normalize_legacy():
    assert normalize_role("USER") == "player"
    assert normalize_role("ops") == "admin"
    assert normalize_role("publisher") == "publisher"


def test_player_no_empresa_write():
    assert role_has_permission("player", "empresa.write") is False
    assert role_has_permission("player", "empresa.read") is False


def test_admin_empresa():
    assert role_has_permission("admin", "empresa.write")
    assert role_has_permission("admin", "empresa.read")


def test_finance_reports_not_users():
    assert role_has_permission("finance", "reports.read")
    assert role_has_permission("finance", "finance.payout")
    assert role_has_permission("finance", "admin.users") is False


def test_super_admin_all():
    perms = permissions_for_role("super_admin")
    assert "empresa.write" in perms
    assert "finance.payout" in perms
    assert role_has_permission("super_admin", "moderation.act")


def test_moderator_not_finance():
    assert role_has_permission("moderator", "moderation.act")
    assert role_has_permission("moderator", "finance.payout") is False


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("OK rbac tests")
