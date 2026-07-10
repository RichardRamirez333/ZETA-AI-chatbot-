/* chat.js — the VERTEX chat application (index.html) */

const Zeta = {
  chatId: null,
  chats: [],
  provider: "openai",
  model: null,
  streaming: false,
  view: "chat", // chat | prompts | images | files
};

const md = (text) => {
  try {
    const raw = marked.parse(text, { breaks: true });
    return raw;
  } catch (e) {
    return escapeHtml(text);
  }
};

/* ============================== CHATS ============================== */

async function loadChats() {
  const { chats } = await apiFetch("/api/chats");
  Zeta.chats = chats;
  renderChatList();
}

function renderChatList(filter = null) {
  const list = document.getElementById("chat-list");
  if (!list) return;
  let chats = Zeta.chats;
  if (filter === "pinned") chats = chats.filter((c) => c.pinned);
  if (filter === "favorite") chats = chats.filter((c) => c.favorite);
  if (!chats.length) {
    list.innerHTML = `<div style="padding:14px 12px; font-size:12.5px; color:var(--text-faint);">No conversations yet.</div>`;
    return;
  }
  list.innerHTML = chats.map((c) => `
    <div class="chat-item ${c.id === Zeta.chatId ? "active" : ""}" data-chat-id="${c.id}">
      ${c.pinned ? `<svg class="pin-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.5 5.5L19 9l-4.5 3.5L16 18l-4-3-4 3 1.5-5.5L5 9l5.5-1.5L12 2z"/></svg>` : ""}
      <span class="title">${escapeHtml(c.title)}</span>
      <div class="chat-actions">
        <button title="Pin" data-action="pin" data-id="${c.id}">${ICONS.pin}</button>
        <button title="Rename" data-action="rename" data-id="${c.id}">${ICONS.edit}</button>
        <button title="Delete" data-action="delete" data-id="${c.id}">${ICONS.trash}</button>
      </div>
    </div>`).join("");

  list.querySelectorAll(".chat-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      openChat(parseInt(el.dataset.chatId));
    });
  });
  list.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = parseInt(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === "pin") {
        const chat = Zeta.chats.find((c) => c.id === id);
        await apiFetch(`/api/chats/${id}/pin`, { method: "POST", body: JSON.stringify({ value: !chat.pinned }) });
        await loadChats();
      } else if (action === "rename") {
        const title = prompt("Rename conversation:");
        if (title) {
          await apiFetch(`/api/chats/${id}/rename`, { method: "POST", body: JSON.stringify({ title }) });
          await loadChats();
        }
      } else if (action === "delete") {
        if (confirm("Delete this conversation? This can't be undone.")) {
          await apiFetch(`/api/chats/${id}`, { method: "DELETE" });
          if (Zeta.chatId === id) newChat();
          await loadChats();
        }
      }
    });
  });
}

async function newChat() {
  Zeta.chatId = null;
  showView("chat");
  renderMessages([]);
  renderChatList();
  document.getElementById("composer-input").focus();
}

async function openChat(id) {
  const data = await apiFetch(`/api/chats/${id}`);
  Zeta.chatId = id;
  Zeta.provider = data.chat.provider;
  Zeta.model = data.chat.model;
  updateModelPickerLabel();
  showView("chat");
  renderMessages(data.messages);
  renderChatList();
  if (window.innerWidth <= 900) {
    document.getElementById("sidebar").classList.remove("mobile-open");
    document.getElementById("sidebar-scrim").classList.remove("show");
  }
}

function renderMessages(messages) {
  const scroll = document.getElementById("chat-scroll");
  if (!messages.length) {
    scroll.innerHTML = emptyStateHTML();
    bindSuggestionCards();
    return;
  }
  scroll.innerHTML = `<div class="chat-inner" id="chat-inner">${messages.map(renderMessageHTML).join("")}</div>`;
  hydrateCodeBlocks();
  bindMessageActions();
  scroll.scrollTop = scroll.scrollHeight;
}

function renderMessageHTML(m) {
  const isUser = m.role === "user";
  return `
  <div class="msg-row ${isUser ? "user" : "assistant"}" data-message-id="${m.id}">
    <div class="msg-avatar">${isUser ? initials(window.VERTEX_USER.display_name) : vertexMonogramSmall()}</div>
    <div class="msg-body">
      <div class="msg-meta">${isUser ? "You" : "VERTEX"}${m.model ? ` · ${m.model}` : ""}</div>
      <div class="msg-content">${md(m.content)}</div>
      <div class="msg-actions">
        <button data-act="copy" title="Copy">${ICONS.copy}</button>
        ${isUser ? `<button data-act="edit" title="Edit">${ICONS.edit}</button>` : `<button data-act="regenerate" title="Regenerate">${ICONS.refresh}</button>`}
        <button data-act="delete" title="Delete">${ICONS.trash}</button>
      </div>
    </div>
  </div>`;
}

function bindMessageActions() {
  document.querySelectorAll(".msg-row").forEach((row) => {
    const id = parseInt(row.dataset.messageId);
    row.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const act = btn.dataset.act;
        if (act === "copy") {
          const text = row.querySelector(".msg-content").innerText;
          navigator.clipboard.writeText(text);
          toast("Copied to clipboard", "success", 1800);
        } else if (act === "delete") {
          await apiFetch(`/api/chats/${Zeta.chatId}/messages/${id}`, { method: "DELETE" });
          const data = await apiFetch(`/api/chats/${Zeta.chatId}`);
          renderMessages(data.messages);
        } else if (act === "edit") {
          const current = row.querySelector(".msg-content").innerText;
          const updated = prompt("Edit message:", current);
          if (updated !== null) {
            await apiFetch(`/api/chats/${Zeta.chatId}/messages/${id}`, { method: "PATCH", body: JSON.stringify({ content: updated }) });
            await sendToStream(updated, true);
          }
        } else if (act === "regenerate") {
          const rows = [...document.querySelectorAll(".msg-row")];
          const idx = rows.indexOf(row);
          const prevUser = rows.slice(0, idx).reverse().find((r) => r.classList.contains("user"));
          if (prevUser) {
            const prevText = prevUser.querySelector(".msg-content").innerText;
            await apiFetch(`/api/chats/${Zeta.chatId}/messages/${id}`, { method: "DELETE" });
            await streamAssistantReply(prevText);
          }
        }
      });
    });
  });
}

function hydrateCodeBlocks() {
  document.querySelectorAll(".msg-content pre code").forEach((el) => {
    if (window.hljs) hljs.highlightElement(el);
  });
}

function emptyStateHTML() {
  return `
  <div class="empty-state">
    <div class="mark">${vertexMonogramLarge()}</div>
    <h1>What can I help with, ${escapeHtml((window.VERTEX_USER.display_name || "there").split(" ")[0])}?</h1>
    <p>Ask anything, brainstorm an idea, or drop in a task. VERTEX routes your message to whichever model you've configured.</p>
    <div class="suggestion-grid">
      <div class="suggestion-card" data-prompt="Explain quantum computing simply">
        <div class="t">Explain a concept</div><div class="s">quantum computing, simply</div>
      </div>
      <div class="suggestion-card" data-prompt="Write a Python function to reverse a linked list">
        <div class="t">Write code</div><div class="s">a linked-list reversal function</div>
      </div>
      <div class="suggestion-card" data-prompt="Draft a professional email declining a meeting">
        <div class="t">Draft a message</div><div class="s">politely decline a meeting</div>
      </div>
      <div class="suggestion-card" data-prompt="Give me 5 marketing angles for a new coffee brand">
        <div class="t">Brainstorm ideas</div><div class="s">marketing angles for coffee</div>
      </div>
    </div>
  </div>`;
}

function bindSuggestionCards() {
  document.querySelectorAll(".suggestion-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.getElementById("composer-input").value = card.dataset.prompt;
      sendMessage();
    });
  });
}

/* ============================== SENDING ============================== */

async function ensureChatExists() {
  if (Zeta.chatId) return Zeta.chatId;
  const { chat } = await apiFetch("/api/chats", {
    method: "POST",
    body: JSON.stringify({ provider: Zeta.provider, model: Zeta.model }),
  });
  Zeta.chatId = chat.id;
  await loadChats();
  return chat.id;
}

async function sendMessage() {
  const input = document.getElementById("composer-input");
  const text = input.value.trim();
  if (!text || Zeta.streaming) return;
  input.value = "";
  autoResize(input);
  await ensureChatExists();

  // optimistic render
  const scroll = document.getElementById("chat-scroll");
  if (!document.getElementById("chat-inner")) {
    scroll.innerHTML = `<div class="chat-inner" id="chat-inner"></div>`;
  }
  const inner = document.getElementById("chat-inner");
  inner.insertAdjacentHTML("beforeend", renderMessageHTML({ id: "tmp-user", role: "user", content: text }));
  scroll.scrollTop = scroll.scrollHeight;

  await streamAssistantReply(text);
  await loadChats();
}

async function streamAssistantReply(userText) {
  Zeta.streaming = true;
  setSendButtonState(true);
  const inner = document.getElementById("chat-inner");
  const assistantId = `streaming-${Date.now()}`;
  inner.insertAdjacentHTML("beforeend", `
    <div class="msg-row assistant" data-message-id="${assistantId}">
      <div class="msg-avatar">${vertexMonogramSmall()}</div>
      <div class="msg-body">
        <div class="msg-meta">VERTEX</div>
        <div class="msg-content" id="${assistantId}"><span class="typing-dots"><span></span><span></span><span></span></span></div>
      </div>
    </div>`);
  const contentEl = document.getElementById(assistantId);
  const scroll = document.getElementById("chat-scroll");
  scroll.scrollTop = scroll.scrollHeight;

  let fullText = "";
  try {
    const res = await fetch(`/api/chats/${Zeta.chatId}/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userText, provider: Zeta.provider, model: Zeta.model }),
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.error || `Stream error (${res.status})`);
    }
    if (!res.body) throw new Error("Streaming not supported by this browser");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        if (!part.startsWith("data:")) continue;
        const jsonStr = part.slice(5).trim();
        if (!jsonStr) continue;
        const evt = JSON.parse(jsonStr);
        if (evt.type === "chunk") {
          fullText += evt.content;
          contentEl.innerHTML = md(fullText);
          scroll.scrollTop = scroll.scrollHeight;
        } else if (evt.type === "error") {
          contentEl.innerHTML = `<span style="color:var(--danger)">${escapeHtml(evt.message)}</span>`;
          toast(evt.message, "error");
        }
      }
    }
  } catch (e) {
    contentEl.innerHTML = `<span style="color:var(--danger)">Connection error: ${escapeHtml(e.message)}</span>`;
  } finally {
    hydrateCodeBlocks();
    Zeta.streaming = false;
    setSendButtonState(false);
    if (Zeta.chatId) {
      const data = await apiFetch(`/api/chats/${Zeta.chatId}`);
      renderMessages(data.messages);
    }
  }
}

function setSendButtonState(isStreaming) {
  const btn = document.getElementById("send-btn");
  if (!btn) return;
  btn.disabled = isStreaming;
  btn.innerHTML = isStreaming
    ? `<svg viewBox="0 0 24 24" width="14" height="14"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/></svg>`
    : ICONS.send;
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 220) + "px";
}

/* ============================== MODEL PICKER ============================== */

function updateModelPickerLabel() {
  const label = document.getElementById("model-picker-label");
  if (!label) return;
  const cfg = window.VERTEX_CONFIG.providers[Zeta.provider];
  label.textContent = `${cfg.label} · ${Zeta.model || cfg.default_model}`;
}

function renderModelModal() {
  const list = document.getElementById("model-list");
  const providers = window.VERTEX_CONFIG.providers;
  list.innerHTML = Object.entries(providers).map(([key, p]) => `
    <div class="settings-row" style="cursor:pointer" data-provider="${key}">
      <div class="info">
        <div class="t">${p.label}</div>
        <div class="s">${p.default_model}</div>
      </div>
      ${key === Zeta.provider ? '<span class="badge">Active</span>' : ""}
    </div>`).join("");
  list.querySelectorAll("[data-provider]").forEach((row) => {
    row.addEventListener("click", () => {
      Zeta.provider = row.dataset.provider;
      Zeta.model = providers[Zeta.provider].default_model;
      updateModelPickerLabel();
      closeModal("model-modal");
    });
  });
}

/* ============================== VIEWS ============================== */

function showView(view) {
  Zeta.view = view;
  document.querySelectorAll(".vertex-view").forEach((v) => (v.style.display = "none"));
  const el = document.getElementById(`view-${view}`);
  if (el) el.style.display = "flex";
  document.querySelectorAll(".nav-item[data-view]").forEach((n) => {
    n.classList.toggle("active", n.dataset.view === view);
  });
  if (view === "prompts") loadPrompts();
  if (view === "images") loadImages();
  if (view === "files") loadFiles();
}

/* ============================== PROMPT LIBRARY ============================== */

async function loadPrompts(category = "All", q = "") {
  const params = new URLSearchParams();
  if (category !== "All") params.set("category", category);
  if (q) params.set("q", q);
  const data = await apiFetch(`/api/prompts?${params}`);
  renderPromptCategories(data.categories, category);
  renderPromptGrid(data.prompts);
}

function renderPromptCategories(categories, active) {
  const tabs = document.getElementById("prompt-tabs");
  const all = ["All", ...categories];
  tabs.innerHTML = all.map((c) => `<div class="tab ${c === active ? "active" : ""}" data-cat="${c}">${c}</div>`).join("");
  tabs.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => loadPrompts(t.dataset.cat, document.getElementById("prompt-search").value)));
}

function renderPromptGrid(prompts) {
  const grid = document.getElementById("prompt-grid");
  if (!prompts.length) {
    grid.innerHTML = `<div style="color:var(--text-faint); font-size:13.5px;">No prompts yet — create your first one.</div>`;
    return;
  }
  grid.innerHTML = prompts.map((p) => `
    <div class="prompt-card" data-id="${p.id}">
      <div class="cat">${escapeHtml(p.category)}</div>
      <div class="t">${escapeHtml(p.title)} ${p.is_favorite ? "★" : ""}</div>
      <div class="c">${escapeHtml(p.content)}</div>
    </div>`).join("");
  grid.querySelectorAll(".prompt-card").forEach((card) => {
    card.addEventListener("click", () => openPromptDetail(parseInt(card.dataset.id), prompts));
  });
}

function openPromptDetail(id, prompts) {
  const p = prompts.find((x) => x.id === id);
  document.getElementById("prompt-detail-title").value = p.title;
  document.getElementById("prompt-detail-content").value = p.content;
  document.getElementById("prompt-detail-category").value = p.category;
  document.getElementById("prompt-detail-fav").checked = !!p.is_favorite;
  document.getElementById("prompt-detail-form").dataset.id = id;
  openModal("prompt-detail-modal");
}

async function usePromptInChat(text) {
  showView("chat");
  document.getElementById("composer-input").value = text;
  autoResize(document.getElementById("composer-input"));
  document.getElementById("composer-input").focus();
}

/* ============================== IMAGE GENERATOR ============================== */

async function loadImages() {
  const { images } = await apiFetch("/api/images");
  const grid = document.getElementById("image-grid");
  if (!images.length) {
    grid.innerHTML = `<div style="color:var(--text-faint); font-size:13.5px;">Your generated images will appear here.</div>`;
    return;
  }
  grid.innerHTML = images.map((img) => `
    <div class="image-card" data-id="${img.id}">
      <img src="${img.image_path}" alt="${escapeHtml(img.prompt)}" loading="lazy"/>
      <div class="overlay">
        <button class="icon-btn" data-dl="${img.image_path}" title="Download">${ICONS.download}</button>
        <button class="icon-btn" data-del="${img.id}" title="Delete">${ICONS.trash}</button>
      </div>
    </div>`).join("");
  grid.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async (e) => {
    e.stopPropagation();
    await apiFetch(`/api/images/${b.dataset.del}`, { method: "DELETE" });
    loadImages();
  }));
  grid.querySelectorAll("[data-dl]").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    window.open(b.dataset.dl, "_blank");
  }));
}

async function loadFiles() {
  const { images } = await apiFetch("/api/images");
  const list = document.getElementById("files-list");
  if (!images.length) {
    list.innerHTML = `<div style="color:var(--text-faint); font-size:13.5px;">No files yet. Generated images and uploads will show up here.</div>`;
    return;
  }
  list.innerHTML = images.map((img) => `
    <div class="settings-row">
      <div class="info"><div class="t">${escapeHtml(img.prompt.slice(0, 60))}</div><div class="s">${img.created_at}</div></div>
      <a class="btn btn-ghost" href="${img.image_path}" target="_blank">Open</a>
    </div>`).join("");
}

/* ============================== ICONS ============================== */

const ICONS = {
  pin: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 2l1.5 5.5L19 9l-4.5 3.5L16 18l-4-3-4 3 1.5-5.5L5 9l5.5-1.5L12 2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`,
  edit: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  trash: `<svg viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4h8v2m-9 0l1 14h8l1-14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  copy: `<svg viewBox="0 0 24 24" fill="none"><rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/><path d="M5 15V5a2 2 0 012-2h10" stroke="currentColor" stroke-width="1.6"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none"><path d="M20 12a8 8 0 10-2.9 6.1M20 12V6m0 6h-6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  send: `<svg viewBox="0 0 24 24" fill="none"><path d="M4 11l16-7-6 16-3-7-7-2z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>`,
  download: `<svg viewBox="0 0 24 24" fill="none"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

function vertexMonogramSmall() {
  return `<svg viewBox="0 0 34 34" width="18" height="18"><path d="M8 9h18l-16 16h17" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
function vertexMonogramLarge() {
  return `<svg viewBox="0 0 56 56"><path d="M12 14h30l-27 27h29" stroke="currentColor" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}

/* ============================== INIT ============================== */

document.addEventListener("DOMContentLoaded", async () => {
  Zeta.provider = window.VERTEX_DEFAULT_PROVIDER || "openai";
  Zeta.model = window.VERTEX_CONFIG.providers[Zeta.provider].default_model;
  updateModelPickerLabel();

  document.getElementById("new-chat-btn").addEventListener("click", newChat);
  document.getElementById("send-btn").addEventListener("click", sendMessage);
  const input = document.getElementById("composer-input");
  input.addEventListener("input", () => autoResize(input));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById("model-picker").addEventListener("click", () => {
    renderModelModal();
    openModal("model-modal");
  });

  document.querySelectorAll(".nav-item[data-view]").forEach((n) => {
    n.addEventListener("click", () => showView(n.dataset.view));
  });
  document.getElementById("nav-pinned").addEventListener("click", () => { showView("chat"); renderChatList("pinned"); });
  document.getElementById("nav-favorites").addEventListener("click", () => { showView("chat"); renderChatList("favorite"); });

  const searchInput = document.getElementById("sidebar-search");
  searchInput.addEventListener("input", debounce(async () => {
    const q = searchInput.value.trim();
    if (!q) return loadChats();
    const { chats } = await apiFetch(`/api/chats?q=${encodeURIComponent(q)}`);
    Zeta.chats = chats;
    renderChatList();
  }, 300));

  // prompt library
  document.getElementById("new-prompt-btn").addEventListener("click", () => {
    document.getElementById("prompt-detail-title").value = "";
    document.getElementById("prompt-detail-content").value = "";
    document.getElementById("prompt-detail-category").value = "AI";
    document.getElementById("prompt-detail-fav").checked = false;
    delete document.getElementById("prompt-detail-form").dataset.id;
    openModal("prompt-detail-modal");
  });
  document.getElementById("prompt-search").addEventListener("input", debounce((e) => {
    loadPrompts(document.querySelector("#prompt-tabs .tab.active")?.dataset.cat || "All", e.target.value);
  }, 300));
  document.getElementById("prompt-detail-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      title: document.getElementById("prompt-detail-title").value,
      content: document.getElementById("prompt-detail-content").value,
      category: document.getElementById("prompt-detail-category").value,
      is_favorite: document.getElementById("prompt-detail-fav").checked,
    };
    if (form.dataset.id) {
      await apiFetch(`/api/prompts/${form.dataset.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      toast("Prompt updated", "success");
    } else {
      await apiFetch("/api/prompts", { method: "POST", body: JSON.stringify(payload) });
      toast("Prompt saved", "success");
    }
    closeModal("prompt-detail-modal");
    loadPrompts();
  });
  document.getElementById("prompt-use-btn").addEventListener("click", () => {
    usePromptInChat(document.getElementById("prompt-detail-content").value);
    closeModal("prompt-detail-modal");
  });
  document.getElementById("prompt-delete-btn").addEventListener("click", async () => {
    const id = document.getElementById("prompt-detail-form").dataset.id;
    if (id && confirm("Delete this prompt?")) {
      await apiFetch(`/api/prompts/${id}`, { method: "DELETE" });
      closeModal("prompt-detail-modal");
      loadPrompts();
    }
  });

  // image generator
  document.getElementById("image-gen-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("image-gen-submit");
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = "Generating…";
    try {
      const payload = {
        prompt: document.getElementById("img-prompt").value,
        negative_prompt: document.getElementById("img-negative").value,
        provider: document.getElementById("img-provider").value,
        aspect_ratio: document.getElementById("img-aspect").value,
        size: document.getElementById("img-size").value,
        seed: document.getElementById("img-seed").value || null,
        steps: document.getElementById("img-steps").value || null,
        cfg_scale: document.getElementById("img-cfg").value || null,
      };
      await apiFetch("/api/images/generate", { method: "POST", body: JSON.stringify(payload) });
      toast("Image generated", "success");
      loadImages();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });

  await loadChats();
  showView("chat");
  newChat();
});
