"""
chat.py
Conversation CRUD + the streaming bridge to whichever AI provider the user
has configured (their own API key, decrypted only in memory for the
duration of the request - see crypto_utils.py / models.get_decrypted_key).
"""
import json
import requests
from flask import Blueprint, request, jsonify, Response, session, stream_with_context

import models
from auth import login_required, current_user
from settings import APP_CONFIG

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chats", methods=["GET"])
@login_required
def api_list_chats():
    q = request.args.get("q")
    uid = session["user_id"]
    chats = models.search_chats(uid, q) if q else models.list_chats(uid)
    return jsonify({"chats": chats})


@chat_bp.route("/api/chats", methods=["POST"])
@login_required
def api_create_chat():
    data = request.get_json(silent=True) or {}
    uid = session["user_id"]
    provider = data.get("provider", "openai")
    model = data.get("model") or APP_CONFIG["providers"].get(provider, {}).get("default_model")
    chat_id = models.create_chat(uid, title=data.get("title", "New Chat"), provider=provider, model=model)
    return jsonify({"chat": models.get_chat(chat_id, uid)})


@chat_bp.route("/api/chats/<int:chat_id>", methods=["GET"])
@login_required
def api_get_chat(chat_id):
    uid = session["user_id"]
    chat = models.get_chat(chat_id, uid)
    if not chat:
        return jsonify({"error": "not_found"}), 404
    messages = models.get_messages(chat_id)
    return jsonify({"chat": chat, "messages": messages})


@chat_bp.route("/api/chats/<int:chat_id>/rename", methods=["POST"])
@login_required
def api_rename_chat(chat_id):
    uid = session["user_id"]
    title = (request.get_json(silent=True) or {}).get("title", "New Chat").strip()[:120]
    models.rename_chat(chat_id, uid, title or "New Chat")
    return jsonify({"ok": True})


@chat_bp.route("/api/chats/<int:chat_id>/pin", methods=["POST"])
@login_required
def api_pin_chat(chat_id):
    uid = session["user_id"]
    value = (request.get_json(silent=True) or {}).get("value", True)
    models.set_chat_flag(chat_id, uid, "pinned", value)
    return jsonify({"ok": True})


@chat_bp.route("/api/chats/<int:chat_id>/favorite", methods=["POST"])
@login_required
def api_favorite_chat(chat_id):
    uid = session["user_id"]
    value = (request.get_json(silent=True) or {}).get("value", True)
    models.set_chat_flag(chat_id, uid, "favorite", value)
    return jsonify({"ok": True})


@chat_bp.route("/api/chats/<int:chat_id>", methods=["DELETE"])
@login_required
def api_delete_chat(chat_id):
    uid = session["user_id"]
    models.delete_chat(chat_id, uid)
    return jsonify({"ok": True})


@chat_bp.route("/api/chats/<int:chat_id>/messages/<int:message_id>", methods=["DELETE"])
@login_required
def api_delete_message(chat_id, message_id):
    models.delete_message(message_id)
    return jsonify({"ok": True})


@chat_bp.route("/api/chats/<int:chat_id>/messages/<int:message_id>", methods=["PATCH"])
@login_required
def api_edit_message(chat_id, message_id):
    content = (request.get_json(silent=True) or {}).get("content", "")
    models.update_message(message_id, content)
    models.truncate_after(chat_id, message_id)
    return jsonify({"ok": True})


# ------------------------------------------------------------ streaming --

@chat_bp.route("/api/chats/<int:chat_id>/stream", methods=["POST"])
@login_required
def api_stream(chat_id):
    """
    Streams an assistant reply as Server-Sent Events.
    Body: { message: str, provider: str, model: str }
    """
    uid = session["user_id"]
    chat = models.get_chat(chat_id, uid)
    if not chat:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    provider = data.get("provider") or chat["provider"] or "openai"
    model = data.get("model") or chat["model"] or APP_CONFIG["providers"][provider]["default_model"]

    if user_message:
        models.add_message(chat_id, "user", user_message)
        if models.get_messages(chat_id) and len(models.get_messages(chat_id)) <= 2:
            models.rename_chat(chat_id, uid, user_message[:60])

    history = models.get_messages(chat_id)
    api_key = models.get_decrypted_key(uid, provider)

    if not api_key and provider != "ollama":
        def err_stream():
            msg = f"No API key configured for {provider}."
            if provider == "openrouter":
                msg += " Get a free key at https://openrouter.ai/keys (free signup, includes $1 credit)."
            else:
                msg += " Add one in Settings → API Keys."
            yield _sse({"type": "error", "message": msg})
        return Response(stream_with_context(err_stream()), mimetype="text/event-stream")

    def generate():
        full_text = ""
        try:
            for chunk in _stream_provider(provider, model, api_key, history):
                full_text += chunk
                yield _sse({"type": "chunk", "content": chunk})
        except Exception as e:
            yield _sse({"type": "error", "message": str(e)})
        finally:
            if full_text:
                models.add_message(chat_id, "assistant", full_text, model=model)
            yield _sse({"type": "done"})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


def _sse(obj):
    return f"data: {json.dumps(obj)}\n\n"


def _stream_provider(provider, model, api_key, history):
    """Yields text chunks. Dispatches to the correct wire format per provider."""
    cfg = APP_CONFIG["providers"][provider]
    ptype = cfg["type"]

    if ptype == "openai_compatible":
        yield from _stream_openai_compatible(cfg["base_url"], api_key, model, history)
    elif ptype == "anthropic":
        yield from _stream_anthropic(cfg["base_url"], api_key, model, history)
    elif ptype == "gemini":
        yield from _stream_gemini(cfg["base_url"], api_key, model, history)
    elif ptype == "ollama":
        yield from _stream_ollama(cfg["base_url"], model, history)
    else:
        raise ValueError(f"Unknown provider type: {ptype}")


def _to_openai_messages(history):
    return [{"role": m["role"], "content": m["content"]} for m in history]


def _stream_openai_compatible(base_url, api_key, model, history):
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if "deepseek" in base_url:
        headers["x-ai-provider"] = "deepseek"  # best effort
    payload = {"model": model, "messages": _to_openai_messages(history), "stream": True}
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Provider error {r.status_code}: {r.text[:300]}")
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            payload_str = line[len("data:"):].strip()
            if payload_str == "[DONE]":
                break
            try:
                obj = json.loads(payload_str)
                delta = obj["choices"][0]["delta"].get("content")
                if delta:
                    yield delta
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


def _stream_anthropic(base_url, api_key, model, history):
    url = f"{base_url}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": _to_openai_messages(history),
        "stream": True,
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Anthropic error {r.status_code}: {r.text[:300]}")
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[len("data:"):].strip())
                if obj.get("type") == "content_block_delta":
                    text = obj.get("delta", {}).get("text")
                    if text:
                        yield text
            except json.JSONDecodeError:
                continue


def _stream_gemini(base_url, api_key, model, history):
    url = f"{base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
    system_instruction = None
    msgs = []
    for m in history:
        if m["role"] == "system":
            system_instruction = {"parts": {"text": m["content"]}}
        else:
            msgs.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]})
    contents = msgs
    payload = {"contents": contents}
    if system_instruction:
        payload["system_instruction"] = system_instruction
    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:300]}")
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[len("data:"):].strip())
                text = obj["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    yield text
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


def _stream_ollama(base_url, model, history):
    url = f"{base_url}/api/chat"
    payload = {"model": model, "messages": _to_openai_messages(history), "stream": True}
    with requests.post(url, json=payload, stream=True, timeout=120) as r:
        if r.status_code != 200:
            raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:300]}")
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
                text = obj.get("message", {}).get("content")
                if text:
                    yield text
            except json.JSONDecodeError:
                continue
