/* main.js — shared utilities: toasts, modals, sidebar behavior, ripple, fetch helper */

async function apiFetch(url, opts = {}) {
  const headers = opts.body instanceof FormData
    ? {}
    : { "Content-Type": "application/json" };
  const res = await fetch(url, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  let body = {};
  try { body = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`);
  return body;
}

/* ---------------------------- Toasts ---------------------------- */
function ensureToastContainer() {
  let c = document.querySelector(".toast-container");
  if (!c) {
    c = document.createElement("div");
    c.className = "toast-container";
    document.body.appendChild(c);
  }
  return c;
}

const TOAST_ICONS = {
  success: `<svg viewBox="0 0 24 24" fill="none" class="icon"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  error: `<svg viewBox="0 0 24 24" fill="none" class="icon"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 8v5M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
  info: `<svg viewBox="0 0 24 24" fill="none" class="icon"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 11v5M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
};

function toast(message, type = "info", duration = 3800) {
  const container = ensureToastContainer();
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `${TOAST_ICONS[type] || TOAST_ICONS.info}<span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity .3s ease, transform .3s ease";
    el.style.opacity = "0";
    el.style.transform = "translateX(30px)";
    setTimeout(() => el.remove(), 300);
  }, duration);
}

/* ---------------------------- Modals ---------------------------- */
function openModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) overlay.classList.add("open");
}
function closeModal(id) {
  const overlay = document.getElementById(id);
  if (overlay) overlay.classList.remove("open");
}
document.addEventListener("click", (e) => {
  if (e.target.classList && e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.open").forEach((m) => m.classList.remove("open"));
  }
});

/* ---------------------------- Ripple ---------------------------- */
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn, .send-btn, .icon-btn, .new-chat-btn");
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  const size = Math.max(rect.width, rect.height);
  ripple.style.width = ripple.style.height = `${size}px`;
  ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
  btn.style.position = btn.style.position || "relative";
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 500);
});

/* ---------------------------- Sidebar ---------------------------- */
function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  const collapseBtn = document.getElementById("collapse-btn");
  const mobileToggle = document.getElementById("mobile-menu-btn");
  const scrim = document.getElementById("sidebar-scrim");

  if (collapseBtn) {
    collapseBtn.addEventListener("click", () => {
      if (window.innerWidth <= 900) {
        sidebar.classList.remove("mobile-open");
        scrim && scrim.classList.remove("show");
        return;
      }
      const collapsed = sidebar.classList.toggle("collapsed");
      localStorage.setItem("zeta_sidebar_collapsed", collapsed ? "1" : "0");
    });
  }
  if (localStorage.getItem("zeta_sidebar_collapsed") === "1" && window.innerWidth > 900) {
    sidebar && sidebar.classList.add("collapsed");
  }
  if (mobileToggle) {
    mobileToggle.addEventListener("click", () => {
      sidebar.classList.add("mobile-open");
      scrim && scrim.classList.add("show");
    });
  }
  if (scrim) {
    scrim.addEventListener("click", () => {
      sidebar.classList.remove("mobile-open");
      scrim.classList.remove("show");
    });
  }
}

/* ---------------------------- Logout ---------------------------- */
async function doLogout() {
  try {
    const body = await apiFetch("/api/auth/logout", { method: "POST" });
    window.location.href = body.redirect || "/login";
  } catch (e) {
    toast("Could not log out. Try again.", "error");
  }
}

/* ---------------------------- User Dropdown ---------------------------- */
function initUserDropdown() {
  const chip = document.getElementById("user-chip");
  const menu = document.getElementById("userDropdownMenu");
  if (!chip || !menu) return;
  chip.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("open");
    chip.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!chip.contains(e.target)) {
      menu.classList.remove("open");
      chip.classList.remove("open");
    }
  });
}

/* ---------------------------- Avatar Upload from Sidebar ---------------------------- */
function initAvatarUpload() {
  const input = document.getElementById("avatar-upload-input");
  if (!input) return;
  input.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("avatar", file);
    try {
      const res = await fetch("/api/profile/avatar", { method: "POST", body: fd });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || "Upload failed");
      const sidebarAvatar = document.getElementById("sidebar-avatar") || document.getElementById("sidebar-avatar-initials");
      const img = document.createElement("img");
      img.className = "avatar";
      img.id = "sidebar-avatar";
      img.src = body.avatar_path + "?t=" + Date.now();
      if (sidebarAvatar) sidebarAvatar.replaceWith(img);
      toast("Profile photo updated", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  initUserDropdown();
  initAvatarUpload();
  document.querySelectorAll("[data-logout]").forEach((el) => el.addEventListener("click", doLogout));
  document.querySelectorAll("[data-close-modal]").forEach((el) =>
    el.addEventListener("click", () => closeModal(el.getAttribute("data-close-modal")))
  );
  document.querySelectorAll("[data-open-modal]").forEach((el) =>
    el.addEventListener("click", () => openModal(el.getAttribute("data-open-modal")))
  );
});

/* ---------------------------- Small helpers ---------------------------- */
function initials(name) {
  if (!name) return "Z";
  const parts = name.trim().split(/\s+/);
  return (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function debounce(fn, delay = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}
