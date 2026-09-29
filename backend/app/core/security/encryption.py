"""
AES-256 encryption for the Credentials Vault (Gap H5).
Used to encrypt/decrypt third-party API keys stored in the database.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import get_settings


def _derive_key(encryption_key: str) -> bytes:
    """Derive a Fernet-compatible key from the raw encryption key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"digital-marketing-ai-vault",  # Fixed salt (key rotation uses key_id)
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
    return key


def get_cipher() -> Fernet:
    """Get a Fernet cipher instance using the app's encryption key."""
    settings = get_settings()
    key = _derive_key(settings.encryption_key)
    return Fernet(key)


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a string value. Returns encrypted bytes for database storage."""
    cipher = get_cipher()
    return cipher.encrypt(plaintext.encode("utf-8"))


def decrypt_value(encrypted: bytes) -> str:
    """Decrypt encrypted bytes back to a string."""
    cipher = get_cipher()
    return cipher.decrypt(encrypted).decode("utf-8")
