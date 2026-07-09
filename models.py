"""
models.py
Thin data-access functions used by auth.py, chat.py, api.py.
Every function takes/returns plain dicts so templates & JSON responses
can consume them directly.
"""
import secrets
import datetime
from database import get_db
from crypto_utils import encrypt_value, decrypt_value, mask_key

# ---------------------------------------------------------------- users ---

def create_user(username, email, password_hash, display_name=None):
    db = get_db()
    cur = db.execute(
        "INSERT INTO users (username, email, password_hash, display_name) "
        "VALUES (?, ?, ?, ?)",
        (username, email, password_hash, display_name or username),
    )
    db.commit()
    return cur.lastrowid


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_username(username):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def update_user_fields(user_id, **fields):
    if not fields:
        return
    db = get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    db.execute(f"UPDATE users SET {cols} WHERE id = ?", (*fields.values(), user_id))
    db.commit()


def set_reset_token(user_id, token, expires_iso):
    update_user_fields(user_id, reset_token=token, reset_token_expires=expires_iso)


def get_user_by_reset_token(token):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE reset_token = ?", (token,)).fetchone()
    return dict(row) if row else None


def delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


def generate_token():
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------- chats ---

def create_chat(user_id, title="New Chat", provider="openai", model=None):
    db = get_db()
    cur = db.execute(
        "INSERT INTO chats (user_id, title, provider, model) VALUES (?, ?, ?, ?)",
        (user_id, title, provider, model),
    )
    db.commit()
    return cur.lastrowid


def list_chats(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM chats WHERE user_id = ? ORDER BY pinned DESC, updated_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_chat(chat_id, user_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)
    ).fetchone()
    return dict(row) if row else None


def touch_chat(chat_id):
    db = get_db()
    db.execute(
        "UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,)
    )
    db.commit()


def rename_chat(chat_id, user_id, title):
    db = get_db()
    db.execute(
        "UPDATE chats SET title = ? WHERE id = ? AND user_id = ?",
        (title, chat_id, user_id),
    )
    db.commit()


def set_chat_flag(chat_id, user_id, field, value):
    assert field in ("pinned", "favorite")
    db = get_db()
    db.execute(
        f"UPDATE chats SET {field} = ? WHERE id = ? AND user_id = ?",
        (1 if value else 0, chat_id, user_id),
    )
    db.commit()


def delete_chat(chat_id, user_id):
    db = get_db()
    db.execute("DELETE FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
    db.commit()


def search_chats(user_id, query):
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT c.* FROM chats c LEFT JOIN messages m ON m.chat_id = c.id "
        "WHERE c.user_id = ? AND (c.title LIKE ? OR m.content LIKE ?) "
        "ORDER BY c.updated_at DESC",
        (user_id, f"%{query}%", f"%{query}%"),
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- messages ---

def add_message(chat_id, role, content, model=None):
    db = get_db()
    cur = db.execute(
        "INSERT INTO messages (chat_id, role, content, model) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, model),
    )
    db.commit()
    touch_chat(chat_id)
    return cur.lastrowid


def get_messages(chat_id, limit=None, before_id=None):
    db = get_db()
    q = "SELECT * FROM messages WHERE chat_id = ?"
    params = [chat_id]
    if before_id:
        q += " AND id < ?"
        params.append(before_id)
    q += " ORDER BY id ASC"
    rows = db.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def delete_message(message_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    db.commit()


def update_message(message_id, content):
    db = get_db()
    db.execute("UPDATE messages SET content = ? WHERE id = ?", (content, message_id))
    db.commit()


def truncate_after(chat_id, message_id):
    """Delete every message after `message_id` in a chat (used on regenerate/edit)."""
    db = get_db()
    db.execute(
        "DELETE FROM messages WHERE chat_id = ? AND id > ?", (chat_id, message_id)
    )
    db.commit()


# --------------------------------------------------------------- prompts --

def create_prompt(user_id, title, content, category):
    db = get_db()
    cur = db.execute(
        "INSERT INTO prompts (user_id, title, content, category) VALUES (?, ?, ?, ?)",
        (user_id, title, content, category),
    )
    db.commit()
    return cur.lastrowid


def list_prompts(user_id, category=None, query=None):
    db = get_db()
    sql = "SELECT * FROM prompts WHERE user_id IN (0, ?)"
    params = [user_id]
    if category and category != "All":
        sql += " AND category = ?"
        params.append(category)
    if query:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]
    sql += " ORDER BY is_favorite DESC, created_at DESC"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def update_prompt(prompt_id, user_id, **fields):
    db = get_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    db.execute(
        f"UPDATE prompts SET {cols} WHERE id = ? AND (user_id = ? OR user_id = 0)",
        (*fields.values(), prompt_id, user_id),
    )
    db.commit()


def delete_prompt(prompt_id, user_id):
    db = get_db()
    db.execute("DELETE FROM prompts WHERE id = ? AND (user_id = ? OR user_id = 0)", (prompt_id, user_id))
    db.commit()


# -------------------------------------------------------------- api keys --

def upsert_api_key(user_id, provider, plaintext_key, label=None):
    db = get_db()
    enc = encrypt_value(plaintext_key)
    db.execute(
        "INSERT INTO api_keys (user_id, provider, encrypted_key, label) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, provider) DO UPDATE SET encrypted_key = excluded.encrypted_key, label = excluded.label",
        (user_id, provider, enc, label),
    )
    db.commit()


def seed_default_deepseek_key(user_id):
    pass


def list_api_keys(user_id):
    """Returns masked keys only - safe for the browser."""
    db = get_db()
    rows = db.execute(
        "SELECT id, provider, label, created_at, encrypted_key FROM api_keys WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        plain = decrypt_value(d.pop("encrypted_key"))
        d["masked_key"] = mask_key(plain)
        out.append(d)
    return out


def get_decrypted_key(user_id, provider):
    db = get_db()
    row = db.execute(
        "SELECT encrypted_key FROM api_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    ).fetchone()
    if not row:
        return None
    return decrypt_value(row["encrypted_key"])


def delete_api_key(user_id, provider):
    db = get_db()
    db.execute(
        "DELETE FROM api_keys WHERE user_id = ? AND provider = ?", (user_id, provider)
    )
    db.commit()


# ---------------------------------------------------------- user_settings -

def set_setting(user_id, key, value):
    db = get_db()
    db.execute(
        "INSERT INTO user_settings (user_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value",
        (user_id, key, value),
    )
    db.commit()


def get_setting(user_id, key, default=None):
    db = get_db()
    row = db.execute(
        "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
        (user_id, key),
    ).fetchone()
    return row["value"] if row else default


def get_all_settings(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT key, value FROM user_settings WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {r["key"]: r["value"] for r in rows}


# ---------------------------------------------------------------- images --

def create_image_record(user_id, **fields):
    db = get_db()
    cols = ", ".join(fields.keys())
    marks = ", ".join("?" for _ in fields)
    cur = db.execute(
        f"INSERT INTO images (user_id, {cols}) VALUES (?, {marks})",
        (user_id, *fields.values()),
    )
    db.commit()
    return cur.lastrowid


def list_images(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM images WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def delete_image(image_id, user_id):
    db = get_db()
    db.execute("DELETE FROM images WHERE id = ? AND user_id = ?", (image_id, user_id))
    db.commit()
