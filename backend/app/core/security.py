"""Security primitives: passwords (bcrypt), JWT access tokens, refresh hashing, HMAC webhook signing."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .config import get_settings

_ALG = "HS256"


def hash_password(plain: str) -> str:
    import bcrypt

    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    import bcrypt

    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, university_id: str | None, extra: dict | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "uni": university_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.access_token_minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.secret_key, algorithm=_ALG)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.secret_key, algorithms=[_ALG])
    except JWTError as exc:
        from .errors import Unauthorized

        raise Unauthorized("نشست نامعتبر یا منقضی است.") from exc


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash) — only the hash is stored."""
    raw = secrets.token_urlsafe(48)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hmac_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_hmac(secret: str, body: bytes, provided: str) -> bool:
    return hmac.compare_digest(hmac_signature(secret, body), provided or "")


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")
