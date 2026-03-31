from __future__ import annotations

import base64
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("model-gateway")


def generate_key() -> str:
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode("utf-8")


def get_fernet(encryption_key: str) -> Fernet | None:
    if not encryption_key:
        return None
    try:
        key_bytes = base64.urlsafe_b64decode(encryption_key.encode("utf-8"))
        return Fernet(key_bytes)
    except Exception as e:
        logger.error(f"invalid encryption key: {e}")
        return None


def encrypt_value(value: str, fernet: Fernet) -> str:
    if not value:
        return value
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_value(value: str, fernet: Fernet) -> str:
    if not value:
        return value
    try:
        encrypted = base64.urlsafe_b64decode(value.encode("utf-8"))
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode("utf-8")
    except InvalidToken:
        return value
    except Exception as e:
        logger.warning(f"decrypt failed: {e}")
        return value


def is_encrypted(value: str) -> bool:
    if not value:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
        return len(decoded) >= 32
    except Exception:
        return False


class ApiKeyCrypto:
    def __init__(self, encryption_key: str | None = None, enabled: bool = False):
        self._enabled = enabled and bool(encryption_key)
        self._fernet = get_fernet(encryption_key) if encryption_key else None

    def encrypt(self, value: str) -> str:
        if not self._enabled or not self._fernet:
            return value
        return encrypt_value(value, self._fernet)

    def decrypt(self, value: str) -> str:
        if not self._fernet:
            return value
        if not is_encrypted(value):
            return value
        return decrypt_value(value, self._fernet)

    def is_enabled(self) -> bool:
        return self._enabled
