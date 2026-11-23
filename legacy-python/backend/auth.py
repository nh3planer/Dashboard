"""Authentifizierung: Passwort-Hashing (PBKDF2) und JWT."""
import hashlib
import os
import time

import jwt

from backend.db import get_db

SECRET = os.environ.get("DASHBOARD_JWT_SECRET", "dev-secret-please-change")
TOKEN_TTL_SECONDS = 8 * 3600

ROLES = ("geschaeftsfuehrer", "management", "projektleiter", "kunde")


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000).hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    return hash_password(password, salt_hex) == expected_hash


def create_token(user) -> str:
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "full_name": user["full_name"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=["HS256"])


def authenticate(username: str, password: str):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (username,)).fetchone()
    conn.close()
    if not user or not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return user
