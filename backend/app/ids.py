from __future__ import annotations

import secrets


def create_public_id(prefix: str, entropy_bytes: int = 6) -> str:
    return f"{prefix}_{secrets.token_hex(entropy_bytes)}"

