"""
api.py
REST endpoints that aren't chat-streaming related: prompt library,
API key management, user settings/preferences, profile, and image
generation.
"""
import os
import base64
import uuid
import requests
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash

import models
from auth import login_required
from settings import APP_CONFIG

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ------------------------------------------------------------- prompts ---

@api_bp.route("/prompts", methods=["GET"])
@login_required
def list_prompts():
    uid = session["user_id"]
    category = request.args.get("category")
    q = request.args.get("q")
    return jsonify({"prompts": models.list_prompts(uid, category, q),
                     "categories": APP_CONFIG["prompt_categories"]})


@api_bp.route("/prompts", methods=["POST"])
@login_required
def create_prompt():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    category = data.get("category") or "AI"
    if not title or not content:
        return jsonify({"error": "Title and content are required."}), 400
    pid = models.create_prompt(uid, title, content, category)
    return jsonify({"ok": True, "id": pid})


@api_bp.route("/prompts/<int:prompt_id>", methods=["PATCH"])
@login_required
def update_prompt(prompt_id):
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    allowed = {k: v for k, v in data.items() if k in ("title", "content", "category", "is_favorite")}
    if not allowed:
        return jsonify({"error": "Nothing to update."}), 400
    models.update_prompt(prompt_id, uid, **allowed)
    return jsonify({"ok": True})


@api_bp.route("/prompts/<int:prompt_id>", methods=["DELETE"])
@login_required
def delete_prompt(prompt_id):
    models.delete_prompt(prompt_id, session["user_id"])
    return jsonify({"ok": True})


# ------------------------------------------------------------ api keys ---

@api_bp.route("/keys", methods=["GET"])
@login_required
def list_keys():
    uid = session["user_id"]
    return jsonify({"keys": models.list_api_keys(uid), "providers": APP_CONFIG["providers"]})


@api_bp.route("/keys", methods=["POST"])
@login_required
def add_key():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    provider = data.get("provider")
    key = (data.get("key") or "").strip()
    label = data.get("label")
    if provider not in APP_CONFIG["providers"]:
        return jsonify({"error": "Unknown provider."}), 400
    if not key:
        return jsonify({"error": "API key cannot be empty."}), 400
    models.upsert_api_key(uid, provider, key, label)
    return jsonify({"ok": True})


@api_bp.route("/keys/<provider>", methods=["DELETE"])
@login_required
def remove_key(provider):
    models.delete_api_key(session["user_id"], provider)
    return jsonify({"ok": True})


# ------------------------------------------------------------- settings --

@api_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    uid = session["user_id"]
    user = models.get_user_by_id(uid)
    return jsonify({
        "theme": user["theme"],
        "mode": user["mode"],
        "language": user["language"],
        "preferences": models.get_all_settings(uid),
        "config": APP_CONFIG,
    })


@api_bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    top_level = {}
    if "theme" in data and data["theme"] in APP_CONFIG["themes"]:
        top_level["theme"] = data["theme"]
    if "mode" in data and data["mode"] in APP_CONFIG["modes"]:
        top_level["mode"] = data["mode"]
    if "language" in data and data["language"] in APP_CONFIG["language"]["available"]:
        top_level["language"] = data["language"]
    if top_level:
        models.update_user_fields(uid, **top_level)

    for key, value in (data.get("preferences") or {}).items():
        models.set_setting(uid, key, str(value))

    return jsonify({"ok": True})


# -------------------------------------------------------------- profile --

@api_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    user = models.get_user_by_id(session["user_id"])
    user.pop("password_hash", None)
    return jsonify({"user": user})


@api_bp.route("/profile", methods=["POST"])
@login_required
def update_profile():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    fields = {}
    if "display_name" in data:
        fields["display_name"] = (data["display_name"] or "").strip()[:80]
    if fields:
        models.update_user_fields(uid, **fields)
    return jsonify({"ok": True})


@api_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    user = models.get_user_by_id(uid)
    if not check_password_hash(user["password_hash"], data.get("current_password") or ""):
        return jsonify({"error": "Current password is incorrect."}), 400
    new_password = data.get("new_password") or ""
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400
    models.update_user_fields(uid, password_hash=generate_password_hash(new_password))
    return jsonify({"ok": True})


@api_bp.route("/profile/avatar", methods=["POST"])
@login_required
def upload_avatar():
    uid = session["user_id"]
    file = request.files.get("avatar")
    if not file or file.filename == "":
        return jsonify({"error": "No file provided."}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_AVATAR_EXT"]:
        return jsonify({"error": "Unsupported file type."}), 400
    fname = f"avatar_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(fname))
    file.save(path)
    models.update_user_fields(uid, avatar_path=f"/uploads/{secure_filename(fname)}")
    return jsonify({"ok": True, "avatar_path": f"/uploads/{secure_filename(fname)}"})


@api_bp.route("/profile/export", methods=["GET"])
@login_required
def export_account():
    uid = session["user_id"]
    user = models.get_user_by_id(uid)
    user.pop("password_hash", None)
    return jsonify({
        "user": user,
        "chats": [
            {**c, "messages": models.get_messages(c["id"])}
            for c in models.list_chats(uid)
        ],
        "prompts": models.list_prompts(uid),
        "images": models.list_images(uid),
    })


@api_bp.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    user = models.get_user_by_id(uid)
    if not check_password_hash(user["password_hash"], data.get("password") or ""):
        return jsonify({"error": "Password is incorrect."}), 400
    models.delete_user(uid)
    session.clear()
    return jsonify({"ok": True})


# --------------------------------------------------------------- images --

@api_bp.route("/images", methods=["GET"])
@login_required
def list_images():
    return jsonify({"images": models.list_images(session["user_id"])})


@api_bp.route("/images/generate", methods=["POST"])
@login_required
def generate_image():
    """
    Generates an image via the user's configured provider.
    Currently wired for OpenAI's Images API (works with any OpenAI-
    compatible key that supports /images/generations, e.g. OpenAI itself
    or a compatible proxy such as OpenRouter/Together for supported models).
    """
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    negative_prompt = data.get("negative_prompt", "")
    provider = data.get("provider", "openai")
    model = data.get("model") or "dall-e-3"
    size = data.get("size", "1024x1024")
    seed = data.get("seed")
    steps = data.get("steps")
    cfg_scale = data.get("cfg_scale")
    aspect_ratio = data.get("aspect_ratio", "1:1")

    if not prompt:
        return jsonify({"error": "A prompt is required."}), 400

    api_key = models.get_decrypted_key(uid, provider)
    if not api_key:
        return jsonify({"error": f"No API key configured for {provider}. Add one in Settings."}), 400

    cfg = APP_CONFIG["providers"].get(provider)
    if not cfg:
        return jsonify({"error": "Unknown provider."}), 400

    try:
        url = f"{cfg['base_url']}/images/generations"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "prompt": prompt, "size": size, "n": 1}
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code != 200:
            return jsonify({"error": f"Provider error {r.status_code}: {r.text[:300]}"}), 502
        result = r.json()
        image_url_or_b64 = result["data"][0].get("url") or result["data"][0].get("b64_json")

        image_path = image_url_or_b64
        if result["data"][0].get("b64_json"):
            fname = f"gen_{uid}_{uuid.uuid4().hex[:10]}.png"
            fpath = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
            with open(fpath, "wb") as f:
                f.write(base64.b64decode(result["data"][0]["b64_json"]))
            image_path = f"/uploads/{fname}"

        img_id = models.create_image_record(
            uid, prompt=prompt, negative_prompt=negative_prompt, provider=provider,
            model=model, seed=seed, steps=steps, cfg_scale=cfg_scale,
            aspect_ratio=aspect_ratio, image_path=image_path,
        )
        return jsonify({"ok": True, "id": img_id, "image_path": image_path})
    except requests.RequestException as e:
        return jsonify({"error": f"Request failed: {e}"}), 502


@api_bp.route("/images/<int:image_id>", methods=["DELETE"])
@login_required
def delete_image(image_id):
    models.delete_image(image_id, session["user_id"])
    return jsonify({"ok": True})
