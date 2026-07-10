"""
database.py
Database access layer for VERTEX.

Uses SQLite by default (database/users.db). The DB_URL/driver logic is kept
isolated here so swapping to PostgreSQL later only requires changing
`get_connection()` (e.g. to psycopg2) - every other module talks to the
database only through the functions in this file / models.py.
"""
import sqlite3
import os
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "users.db")

os.makedirs(DB_DIR, exist_ok=True)


def get_connection():
    """Return a raw connection. Swap this function to switch DB engines."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Request-scoped connection, cached on flask.g."""
    if "db" not in g:
        g.db = get_connection()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    avatar_path TEXT,
    theme TEXT DEFAULT 'black',
    mode TEXT DEFAULT 'dark',
    language TEXT DEFAULT 'en',
    is_verified INTEGER DEFAULT 0,
    verification_token TEXT,
    reset_token TEXT,
    reset_token_expires TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    encrypted_key TEXT NOT NULL,
    label TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider)
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Chat',
    provider TEXT DEFAULT 'openai',
    model TEXT,
    pinned INTEGER DEFAULT 0,
    favorite INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'AI',
    is_favorite INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    provider TEXT,
    model TEXT,
    seed INTEGER,
    steps INTEGER,
    cfg_scale REAL,
    aspect_ratio TEXT,
    image_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(app=None):
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    if app is not None:
        app.teardown_appcontext(close_db)
        app.before_request(lambda: None)  # ensure g is populated
