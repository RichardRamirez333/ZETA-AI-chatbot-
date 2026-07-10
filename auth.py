"""
auth.py
Full account system: register, login, logout, forgot/reset password,
"remember me" persistent sessions, and a login_required decorator used
by every other protected blueprint.
"""
import re
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from functools import wraps

from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

import models

auth_bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# --- extremely small in-memory rate limiter (per-process) -----------------
_attempts = {}


def _rate_limited(key, limit=8, window=60):
    now = time.time()
    bucket = _attempts.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "authentication_required"}), 401
            return redirect(url_for("auth.login_page", next=request.path))
        if models.get_user_by_id(session["user_id"]) is None:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"error": "authentication_required"}), 401
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    user = models.get_user_by_id(uid)
    if user is None:
        session.clear()
        return None
    return user


# ------------------------------------------------------------------ pages -

@auth_bp.route("/login", methods=["GET"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("register.html")


# ------------------------------------------------------------------- API --

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not USERNAME_RE.match(username):
        return jsonify({"error": "Username must be 3-32 chars: letters, numbers, _ . -"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400
    if models.get_user_by_username(username):
        return jsonify({"error": "That username is already taken."}), 409
    if models.get_user_by_email(email):
        return jsonify({"error": "An account with that email already exists."}), 409

    pw_hash = generate_password_hash(password)
    user_id = models.create_user(username, email, pw_hash, display_name=username)
    models.seed_default_deepseek_key(user_id)
    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    return jsonify({"ok": True, "redirect": url_for("index")})


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if _rate_limited(f"login:{request.remote_addr}"):
        return jsonify({"error": "Too many attempts. Please wait a moment and try again."}), 429

    user = models.get_user_by_username(identifier) or models.get_user_by_email(identifier.lower())
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect username/email or password."}), 401

    models.seed_default_deepseek_key(user["id"])
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = remember
    return jsonify({"ok": True, "redirect": url_for("index")})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True, "redirect": url_for("auth.login_page")})


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    user = models.get_user_by_email(email)

    # Always respond success (don't leak which emails exist)
    if user:
        token = models.generate_token()
        expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
        models.set_reset_token(user["id"], token, expires)
        reset_link = url_for("auth.reset_password_page", token=token, _external=True)
        _send_email(
            to=email,
            subject="Reset your VERTEX password",
            body=f"Click the link below to reset your password (valid 1 hour):\n\n{reset_link}",
        )
    return jsonify({"ok": True, "message": "If that email exists, a reset link has been sent."})


@auth_bp.route("/reset-password/<token>", methods=["GET"])
def reset_password_page(token):
    return render_template("login.html", reset_token=token, show_reset=True)


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or request.form
    token = data.get("token")
    new_password = data.get("password") or ""

    user = models.get_user_by_reset_token(token)
    if not user or not user["reset_token_expires"]:
        return jsonify({"error": "This reset link is invalid or has expired."}), 400
    if datetime.datetime.fromisoformat(user["reset_token_expires"]) < datetime.datetime.utcnow():
        return jsonify({"error": "This reset link has expired."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    models.update_user_fields(
        user["id"],
        password_hash=generate_password_hash(new_password),
        reset_token=None,
        reset_token_expires=None,
    )
    return jsonify({"ok": True, "message": "Password updated. You can now log in."})


def _send_email(to, subject, body):
    """
    Sends via SMTP if configured through environment variables
    (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS). Otherwise, logs the
    message to the console so local/dev usage still works end to end
    without a real mail server.
    """
    import os
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"[VERTEX MAIL - no SMTP configured] To: {to} | Subject: {subject}\n{body}\n")
        return
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        pw = os.environ.get("SMTP_PASS")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, pw)
            server.sendmail(user, [to], msg.as_string())
    except Exception as e:
        print(f"[VERTEX MAIL ERROR] Could not send email to {to}: {e}")
