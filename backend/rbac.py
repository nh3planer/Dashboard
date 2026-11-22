"""Rollen- und Rechteverwaltung (RBAC)."""
from fastapi import HTTPException, Request

ROLE_MANAGEMENT_KPI = ("geschaeftsfuehrer", "management")
ROLE_USER_ADMIN = ("geschaeftsfuehrer",)
ROLE_REPORT_KOSTEN = ("geschaeftsfuehrer", "management", "projektleiter")
ROLE_STANDARD = ("geschaeftsfuehrer", "management", "projektleiter", "kunde")


def current_user(request: Request) -> dict:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        token = request.query_params.get("token", "")
    if not token:
        raise HTTPException(401, "Nicht angemeldet")
    try:
        from backend.auth import decode_token
        payload = decode_token(token)
    except Exception:
        raise HTTPException(401, "Sitzung ungültig oder abgelaufen")
    return payload


def require_roles(allowed):
    def guard(request: Request) -> dict:
        user = current_user(request)
        if user["role"] not in allowed:
            raise HTTPException(403, "Keine Berechtigung für diesen Bereich")
        return user
    return guard
