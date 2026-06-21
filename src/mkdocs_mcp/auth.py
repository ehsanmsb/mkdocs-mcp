"""Authentication wiring built on FastMCP's own auth stack.

Static bearer tokens are verified by FastMCP's ``StaticTokenVerifier`` (no
custom middleware). Each token carries scopes; admin tokens get the ``admin``
scope, which gates admin-only tools via ``require_admin``.

For real deployments you can swap ``build_verifier`` for any FastMCP provider
(``JWTVerifier``, the Keycloak/GitHub/Google OAuth providers, …) without
touching the tools.
"""
from __future__ import annotations

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from .config import Settings

ADMIN_SCOPE = "admin"
READ_SCOPE = "read"


def build_verifier(cfg: Settings) -> StaticTokenVerifier | None:
    """Return a token verifier, or None when auth is disabled."""
    if cfg.auth_mode == "none":
        return None
    tokens: dict[str, dict] = {}
    for tok in cfg.bearer_token_set:
        tokens[tok] = {"client_id": "reader", "scopes": [READ_SCOPE]}
    for tok in cfg.admin_token_set:
        tokens[tok] = {"client_id": "admin", "scopes": [READ_SCOPE, ADMIN_SCOPE]}
    if not tokens:
        return None
    return StaticTokenVerifier(tokens=tokens)


def require_admin() -> None:
    """Raise ``PermissionError`` unless the caller holds the admin scope.

    Uses FastMCP's access-token dependency. When there is no auth context
    (auth disabled, or non-HTTP transport in tests), it is a no-op.
    """
    from fastmcp.server.dependencies import get_access_token

    try:
        token = get_access_token()
    except Exception:  # noqa: BLE001 - no auth context
        return
    if token is None:
        return
    if ADMIN_SCOPE not in (token.scopes or []):
        raise PermissionError("admin scope required for this tool")
