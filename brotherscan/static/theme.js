/* Thème : chargé avant la feuille de style pour éviter tout flash. Sombre par défaut. */
(() => {
  "use strict";
  const KEY = "bs-theme";
  const THEMES = ["dark", "light", "auto"];
  const root = document.documentElement;
  const media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function stored() {
    try {
      const value = localStorage.getItem(KEY);
      return THEMES.includes(value) ? value : "dark";
    } catch (_) {
      return "dark";
    }
  }

  function apply(theme) {
    root.dataset.theme = theme;
    const dark = theme === "dark" || (theme === "auto" && media && media.matches);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = dark ? "#121211" : "#f5f3ee";
  }

  window.ScanTheme = {
    get: stored,
    set(theme) {
      if (!THEMES.includes(theme)) return;
      try { localStorage.setItem(KEY, theme); } catch (_) { /* navigation privée */ }
      apply(theme);
    },
  };

  apply(stored());
  if (media && media.addEventListener) media.addEventListener("change", () => apply(stored()));
})();
