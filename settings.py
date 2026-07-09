"""
settings.py
Application configuration: Flask config values + loader for config.json
(theme palette, provider registry, feature toggles, prompt categories).
"""
import os
import sys
import json
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SECRET_KEY_PATH = os.path.join(BASE_DIR, "database", "flask_secret.key")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SECRET_KEY_PATH), exist_ok=True)


def _load_flask_secret():
    if os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "r") as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(SECRET_KEY_PATH, "w") as f:
        f.write(key)
    return key


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class Config:
    SECRET_KEY = _load_flask_secret()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB upload limit (avatars)
    UPLOAD_FOLDER = UPLOAD_DIR
    ALLOWED_AVATAR_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days "remember me"


APP_CONFIG = load_config()
