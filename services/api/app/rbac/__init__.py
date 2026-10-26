"""Server-side RBAC. Every route declares who may call it via `require(...)`.

`tests/unit/test_authz_matrix.py` introspects the FastAPI app and fails if any
non-public route is missing a `RoleGuard`, so a forgotten check cannot ship.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from services.api.app.auth.routes import TokenPayload, get_current_user

ALL_ROLES = (
    "institution_user",
    "scrutiny_officer",
    "supervisor",
    "auditor",
    "rules_admin",
    "sysadmin",
)
STAFF = ("scrutiny_officer", "supervisor", "auditor", "rules_admin", "sysadmin")
OFFICERS = ("scrutiny_officer", "supervisor", "sysadmin")


class RoleGuard:
    """FastAPI dependency: authenticated user whose role is in `roles`."""

    def __init__(self, roles: tuple[str, ...]):
        self.roles = tuple(roles)

    def __call__(self, user: Annotated[TokenPayload, Depends(get_current_user)]) -> TokenPayload:
        if user.role not in self.roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' is not permitted")
        return user


def require(*roles: str) -> TokenPayload:
    """Use as a parameter default: `user = require('supervisor')`."""
    return Depends(RoleGuard(roles or ALL_ROLES))


# Routes that are intentionally reachable without a role guard.
PUBLIC_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}
# Authenticated, any role (still has a RoleGuard of ALL_ROLES or get_current_user).
ANY_AUTH_PATHS = {
    "/api/auth/me",
}
