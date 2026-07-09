/* theme.js — theme + light/dark/system mode switching, persisted via /api/settings */

const ZetaTheme = (() => {
  function resolveSystemMode() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function apply(theme, mode) {
    const root = document.documentElement;
    const effectiveMode = mode === "system" ? resolveSystemMode() : mode;
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-mode", effectiveMode);
    root.setAttribute("data-mode-pref", mode);
  }

  async function set(theme, mode) {
    apply(theme, mode);
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme, mode }),
      });
    } catch (e) {
      console.error("Failed to save theme", e);
    }
  }

  function init() {
    const root = document.documentElement;
    const modePref = root.getAttribute("data-mode-pref") || root.getAttribute("data-mode") || "dark";
    const theme = root.getAttribute("data-theme") || "black";
    apply(theme, modePref);

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (root.getAttribute("data-mode-pref") === "system") {
        apply(root.getAttribute("data-theme"), "system");
      }
    });
  }

  return { init, set, apply };
})();

document.addEventListener("DOMContentLoaded", ZetaTheme.init);
