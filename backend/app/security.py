from __future__ import annotations

import hashlib
import secrets

from pwdlib import PasswordHash

from app.validation import normalize_security_answer

password_hasher = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hasher.hash(value)


def verify_password(value: str, hashed_value: str) -> bool:
    return password_hasher.verify(value, hashed_value)


def hash_security_answer(value: str) -> str:
    return password_hasher.hash(normalize_security_answer(value))


def verify_security_answer(value: str, hashed_value: str) -> bool:
    return password_hasher.verify(normalize_security_answer(value), hashed_value)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

