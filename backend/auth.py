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


def normalize_username(name: str) -> str:
    return (name.strip().lower()
            .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
            .replace("ß", "ss"))


def username_variants(name: str) -> list:
    variants = [name.strip(), normalize_username(name)]
    return list(dict.fromkeys(v for v in variants if v))


def authenticate(username: str, password: str):
    conn = get_db()
    user = None
    rows = conn.execute("SELECT * FROM users WHERE active = 1").fetchall()
    conn.close()
    input_variants = set(username_variants(username))
    for row in rows:
        stored = {row["username"], row["full_name"]}
        stored |= {normalize_username(s) for s in stored}
        if input_variants & stored:
            user = row
            break
    if not user or not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return user
