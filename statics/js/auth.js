/* auth.js — handles login, register, forgot & reset password forms */

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  const isPw = input.type === "password";
  input.type = isPw ? "text" : "password";
  btn.innerHTML = isPw ? ICON_EYE_OFF : ICON_EYE;
}

const ICON_EYE = `<svg viewBox="0 0 24 24" fill="none" width="18" height="18"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8"/></svg>`;
const ICON_EYE_OFF = `<svg viewBox="0 0 24 24" fill="none" width="18" height="18"><path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 5.1A10.9 10.9 0 0112 5c7 0 11 7 11 7a13.4 13.4 0 01-3.4 4M6.1 6.6C3.6 8.3 2 12 2 12s2 4 6 5.6M14.1 14.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const body = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, body };
}

function bindAuthForm(formId, url, onSuccess) {
  const form = document.getElementById(formId);
  if (!form) return;
  const errorBox = form.querySelector(".error-text");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorBox) errorBox.textContent = "";
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    const original = submitBtn.innerHTML;
    submitBtn.innerHTML = `<span class="typing-dots"><span></span><span></span><span></span></span>`;

    const data = Object.fromEntries(new FormData(form).entries());
    if (form.querySelector('input[name="remember"]')) {
      data.remember = form.querySelector('input[name="remember"]').checked;
    }
    const { ok, body } = await postJSON(url, data);
    submitBtn.disabled = false;
    submitBtn.innerHTML = original;

    if (!ok) {
      if (errorBox) errorBox.textContent = body.error || "Something went wrong.";
      return;
    }
    onSuccess(body, form);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".toggle-visibility").forEach((btn) => { btn.innerHTML = ICON_EYE; });

  bindAuthForm("login-form", "/api/auth/login", (body) => {
    window.location.href = body.redirect || "/";
  });

  bindAuthForm("register-form", "/api/auth/register", (body) => {
    window.location.href = body.redirect || "/";
  });

  bindAuthForm("forgot-form", "/api/auth/forgot-password", (body, form) => {
    const msgBox = document.getElementById("forgot-message");
    if (msgBox) msgBox.textContent = body.message;
    form.reset();
  });

  bindAuthForm("reset-form", "/api/auth/reset-password", (body) => {
    const msgBox = document.getElementById("reset-message");
    if (msgBox) {
      msgBox.textContent = body.message + " Redirecting to login…";
      setTimeout(() => (window.location.href = "/login"), 1600);
    }
  });

  // panel switching on the auth pages (login <-> forgot password)
  document.querySelectorAll("[data-show-panel]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const target = el.getAttribute("data-show-panel");
      document.querySelectorAll(".auth-panel").forEach((p) => (p.style.display = "none"));
      const panel = document.getElementById(target);
      if (panel) panel.style.display = "block";
    });
  });
});
