"""
crypto_utils.py
Symmetric encryption for user-supplied provider API keys.

A local key file (database/secret.key) is generated on first run and is
never sent to the browser. Every API key stored in the `api_keys` table is
encrypted with this key before being written to disk, and decrypted only
in-memory, per-request, when ZETA needs to call a provider on the user's
behalf.
"""
import os
import sys
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "database", "secret.key")


def _load_or_create_key() -> bytes:
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    if sys.platform != "win32":
        os.chmod(KEY_PATH, 0o600)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_value(plaintext: str) -> str:
    if plaintext is None:
        return ""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def mask_key(plaintext: str) -> str:
    """Return a display-safe masked version, e.g. sk-ab12************3f9d"""
    if not plaintext or len(plaintext) < 8:
        return "••••••••"
    return f"{plaintext[:5]}{'•' * 10}{plaintext[-4:]}"
