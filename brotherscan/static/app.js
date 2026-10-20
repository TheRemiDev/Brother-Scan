/* Scan — interface (aucune dépendance) */
(() => {
  "use strict";

  // ---------------------------------------------------------------- icônes
  const ICONS = {
    download: '<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/>',
    send: '<path d="M21 3 10 14"/><path d="m21 3-7 18-4-7-7-4 18-7Z"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    eyeOff: '<path d="M3 3l18 18"/><path d="M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3 3.9M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.8 9.8 0 0 0 5.4-1.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    trash: '<path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/><path d="M9 7V4h6v3"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    arrowRight: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    left: '<path d="m15 6-6 6 6 6"/>',
    right: '<path d="m9 6 6 6-6 6"/>',
    check: '<path d="M5 12.5 10 17 19 7"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    at: '<circle cx="12" cy="12" r="4"/><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8"/>',
    alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.5v.01"/>',
    printer: '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    auto: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  };
  const icon = (name, extra = "") =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" ${extra} aria-hidden="true">${ICONS[name]}</svg>`;

  // ---------------------------------------------------------------- DOM
  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v; // uniquement pour nos icônes statiques
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "style") el.style.cssText = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const child of children.flat()) {
      if (child == null || child === false) continue;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
  }
  const iconEl = (name) => h("span", { html: icon(name), style: "display:contents" });
  const $app = document.getElementById("app");

  // ---------------------------------------------------------------- API
  class ApiError extends Error {
    constructor(status, data) {
      super((data && data.detail) || "Une erreur est survenue.");
      this.status = status;
      this.data = data || {};
    }
  }
  async function api(path, { method = "GET", body } = {}) {
    const res = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (_) { /* vide */ }
    if (res.status === 401 && path !== "/api/login") {
      lockApp();
      throw new ApiError(401, { detail: "Session expirée." });
    }
    if (!res.ok) {
      if (data && Array.isArray(data.detail)) data.detail = "Données invalides.";
      throw new ApiError(res.status, data);
    }
    return data;
  }

  // ---------------------------------------------------------------- formats
  const fmtTime = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" });
  const fmtDay = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", timeZone: "Europe/Paris" });
  const fmtKey = new Intl.DateTimeFormat("fr-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: "Europe/Paris" });

  function dayLabel(ts) {
    const d = new Date(ts * 1000);
    const key = fmtKey.format(d);
    if (key === fmtKey.format(new Date())) return "Aujourd’hui";
    if (key === fmtKey.format(new Date(Date.now() - 864e5))) return "Hier";
    const s = fmtDay.format(d);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
  const timeLabel = (ts) => fmtTime.format(new Date(ts * 1000)).replace(":", " h ");
  const pagesLabel = (n) => `${n} page${n > 1 ? "s" : ""}`;
  function sizeLabel(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} Ko`;
    return `${(bytes / 1024 / 1024).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} Mo`;
  }
  function agoLabel(ts) {
    const s = Math.max(0, Date.now() / 1000 - ts);
    if (s < 60) return "à l’instant";
    if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
    return `il y a ${Math.floor(s / 3600)} h`;
  }
  function expiryLabel(ts) {
    const s = Math.max(0, ts - Date.now() / 1000);
    if (s < 3600) return `Supprimé dans ${Math.max(1, Math.ceil(s / 60))} min`;
    return `Supprimé dans ${Math.floor(s / 3600)} h`;
  }
  const docTitle = (scan) => (scan.kind === "merge" ? "Document fusionné" : "Numérisation");
  const initials = (name) => (name || "?").trim().split(/[\s._-]+/).slice(0, 2).map((p) => p[0] || "").join("").toUpperCase() || "@";

  // ---------------------------------------------------------------- toasts
  function toast(message, type = "ok") {
    const el = h("div", { class: `toast ${type}`, role: "status" }, iconEl(type === "error" ? "alert" : "check"), message);
    document.getElementById("toasts").append(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 320); }, type === "error" ? 4200 : 2600);
  }

  // ---------------------------------------------------------------- état
  const state = {
    info: null,
    scans: [],
    mail: null,
    canSend: true,
    merging: false,
    selection: [],
    contacts: null,
    knownIds: null,
    freshIds: new Set(),
    signature: "",
  };
  let pollTimer = null;

  // ================================================================ PIN
  function lockApp() {
    stopPolling();
    closeAllSheets();
    state.merging = false;
    state.selection = [];
    renderLock();
  }

  function renderLock(message = "") {
    document.title = "Scan";
    const input = h("input", {
      class: "pin-input", type: "password", name: "pin", autocomplete: "current-password",
      placeholder: "Code d’accès", "aria-label": "Code d’accès", autocapitalize: "off", spellcheck: "false",
    });
    const toggle = h("button", { class: "icon-btn pin-toggle", type: "button", "aria-label": "Afficher le code", html: icon("eye") });
    toggle.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      toggle.innerHTML = icon(show ? "eyeOff" : "eye");
      input.focus();
    });
    const error = h("div", { class: "pin-error", role: "alert" }, message);
    const submit = h("button", { class: "btn btn-primary btn-lg btn-block", type: "submit" }, "Déverrouiller", iconEl("arrowRight"));
    const card = h("form", { class: "lock-card", autocomplete: "on" },
      h("div", { class: "lock-mark", "aria-hidden": "true" }),
      h("h1", { class: "wordmark" }, "Scan", h("i", {}, ".")),
      h("p", { class: "lead" }, "Vos numérisations, simplement."),
      h("div", { class: "pin-field" }, input, toggle),
      error,
      submit,
      h("div", { class: "lock-foot" }, "Accès privé · documents supprimés après 24 h"),
    );

    let countdown = null;
    const lockFor = (seconds) => {
      clearInterval(countdown);
      let left = seconds;
      submit.disabled = true;
      const tick = () => {
        if (left <= 0) { clearInterval(countdown); submit.disabled = false; error.textContent = ""; return; }
        error.textContent = `Trop d’essais. Réessayez dans ${left} s.`;
        left -= 1;
      };
      tick();
      countdown = setInterval(tick, 1000);
    };

    card.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!input.value) { input.focus(); return; }
      submit.disabled = true;
      submit.replaceChildren(h("span", { class: "spinner" }));
      try {
        await api("/api/login", { method: "POST", body: { pin: input.value } });
        clearInterval(countdown);
        await enterApp();
      } catch (err) {
        submit.disabled = false;
        submit.replaceChildren("Déverrouiller", iconEl("arrowRight"));
        input.value = "";
        input.focus();
        card.classList.remove("shake");
        void card.offsetWidth;
        card.classList.add("shake");
        if (navigator.vibrate) navigator.vibrate(60);
        error.textContent = err.status === 401 ? "Code incorrect." : err.message;
        if (err.data && err.data.retry_after) lockFor(err.data.retry_after);
      }
    });

    $app.className = "";
    $app.replaceChildren(h("main", { class: "lock" }, card));
    setTimeout(() => input.focus(), 50);
  }

  // ================================================================ application
  async function enterApp() {
    state.signature = "";
    state.knownIds = null;
    await refresh();
    startPolling();
  }

  function startPolling() {
    stopPolling();
    pollTimer = setInterval(() => { if (!document.hidden) refresh().catch(() => {}); }, 6000);
  }
  function stopPolling() { clearInterval(pollTimer); pollTimer = null; }
  document.addEventListener("visibilitychange", () => { if (!document.hidden && pollTimer) refresh().catch(() => {}); });

  async function refresh() {
    const data = await api("/api/scans");
    const ids = data.scans.map((s) => s.id);
    if (state.knownIds) {
      const fresh = ids.filter((id) => !state.knownIds.has(id));
      const incoming = data.scans.filter((s) => fresh.includes(s.id) && s.kind === "scan");
      if (incoming.length) toast(incoming.length > 1 ? `${incoming.length} nouveaux documents reçus` : "Nouveau document reçu");
      fresh.forEach((id) => state.freshIds.add(id));
    }
    state.knownIds = new Set(ids);
    state.scans = data.scans;
    state.mail = data.mail;
    state.canSend = data.can_send;
    state.selection = state.selection.filter((id) => state.knownIds.has(id));
    const signature = JSON.stringify([ids, data.mail.error, data.mail.enabled]);
    if (signature !== state.signature || !$app.querySelector(".shell")) {
      state.signature = signature;
      renderMain();
    } else {
      updateLiveLabels();
    }
  }

  const byId = (id) => state.scans.find((s) => s.id === id);
  const thumbUrl = (scan) => `/api/scans/${scan.id}/thumb`;
  const fileUrl = (scan, inline = false) => `/api/scans/${scan.id}/file${inline ? "?inline=1" : ""}`;

  function paper(scan, { stacked = false, label = true } = {}) {
    const img = h("img", { src: thumbUrl(scan), alt: "", decoding: "async" });
    img.addEventListener("load", () => img.classList.add("ready"));
    img.addEventListener("error", () => img.classList.add("ready"));
    if (img.complete) img.classList.add("ready");
    return h("div", { class: `paper-wrap${stacked ? " stacked" : ""}` },
      h("div", { class: "paper" }, img),
      label ? h("span", { class: "pages-chip" }, pagesLabel(scan.pages)) : null,
    );
  }

  function downloadButton(scan, cls = "btn btn-primary") {
    return h("a", { class: cls, href: fileUrl(scan), download: scan.download_name }, iconEl("download"), "Télécharger");
  }

  function renderMain() {
    const settled = !!$app.querySelector(".shell");
    const scans = state.scans;
    const shell = h("div", { class: `shell${state.merging ? " selecting" : ""}` });

    // -- barre supérieure
    const topbar = h("header", { class: "topbar" },
      h("div", { class: "wordmark" }, "Scan", h("i", {}, ".")),
      h("div", { class: "topbar-actions" },
        h("button", { class: "icon-btn", type: "button", "aria-label": "Réglages", title: "Réglages", html: icon("settings"), onclick: openSettings }),
        h("button", { class: "icon-btn", type: "button", "aria-label": "Verrouiller", title: "Verrouiller", html: icon("lock"), onclick: logout }),
      ),
    );
    shell.append(topbar);

    // -- introduction
    const address = state.info ? state.info.scan_address : "";
    const statusEl = h("div", { class: `status${state.mail && state.mail.error ? " error" : ""}`, "data-live": "status" });
    shell.append(h("section", { class: "intro" },
      h("div", { class: "eyebrow" }, state.merging ? "Fusion" : "Vos documents"),
      h("h2", {}, state.merging ? "Assembler en un seul PDF" : "Numérisations"),
      h("p", {}, "Depuis l’imprimante, envoyez vos documents à ", h("strong", {}, address), ". Ils apparaissent ici automatiquement et sont supprimés après 24 h."),
      statusEl,
    ));

    if (state.merging) {
      shell.append(h("div", { class: "merge-banner" },
        h("span", { class: "num", html: icon("layers") }),
        h("p", {}, h("strong", {}, "Touchez les documents dans l’ordre voulu. "), "Le numéro indique leur position dans le PDF final."),
      ));
      const grid = h("div", { class: "grid" });
      scans.forEach((scan, i) => grid.append(selectableCard(scan, i)));
      shell.append(grid);
    } else if (!scans.length) {
      shell.append(emptyState());
    } else {
      const [latest, ...rest] = scans;
      shell.append(featureCard(latest));
      if (rest.length || scans.length >= 2) {
        shell.append(h("div", { class: "section-head", style: "margin-top:52px" },
          h("div", { class: "eyebrow" }, rest.length ? "Précédentes" : ""),
          scans.length >= 2
            ? h("button", { class: "btn btn-secondary btn-sm", type: "button", onclick: startMerge }, iconEl("layers"), "Fusionner", h("span", { class: "long", style: "margin-left:-.3em" }, "des documents"))
            : null,
        ));
      }
      if (rest.length) {
        const grid = h("div", { class: "grid" });
        rest.forEach((scan, i) => grid.append(card(scan, i)));
        shell.append(grid);
      }
    }

    shell.append(h("div", { class: "foot" }, `Les 10 derniers documents · Scan ${state.info ? state.info.version : ""}`));

    if (state.merging) shell.append(mergeTray());

    if (settled) shell.querySelectorAll(".intro, .feature:not(.fresh), .card:not(.fresh), .empty, .merge-banner").forEach((el) => (el.style.animation = "none"));
    $app.className = "";
    $app.replaceChildren(shell);
    document.body.classList.toggle("locked-scroll", false);
    state.freshIds.clear();
    updateLiveLabels();
  }

  function updateLiveLabels() {
    const status = $app.querySelector('[data-live="status"]');
    if (status && state.mail) {
      let text;
      if (!state.mail.enabled) text = "Relève des e-mails non configurée";
      else if (state.mail.error) text = "Boîte mail injoignable — nouvel essai en cours";
      else if (!state.mail.last_check) text = "Connexion à la boîte mail…";
      else text = `Boîte relevée ${agoLabel(state.mail.last_check)}`;
      status.classList.toggle("error", !state.mail.enabled || state.mail.error);
      status.replaceChildren(h("span", { class: "dot" }), text);
    }
    $app.querySelectorAll("[data-expiry]").forEach((el) => {
      const scan = byId(el.dataset.expiry);
      if (scan) el.lastChild.textContent = expiryLabel(scan.expires_at);
    });
  }
  setInterval(() => { if (!document.hidden) updateLiveLabels(); }, 15000);

  const expiryEl = (scan) => h("span", { class: "expiry", "data-expiry": scan.id }, iconEl("clock"), h("span", {}, expiryLabel(scan.expires_at)));

  function featureCard(scan) {
    const isMerge = scan.kind === "merge";
    return h("article", { class: `feature${state.freshIds.has(scan.id) ? " fresh" : ""}` },
      h("button", { class: "paper-wrap-btn", type: "button", style: "all:unset;cursor:pointer;display:block", "aria-label": "Aperçu", onclick: () => openViewer(scan) },
        paper(scan, { stacked: scan.pages > 1 })),
      h("div", { class: "feature-info" },
        h("span", { class: `badge${isMerge ? "" : " gold"}` }, isMerge ? `Fusion · ${scan.sources.length} documents` : "Dernière numérisation"),
        h("h3", {}, `${dayLabel(scan.created_at)}, ${timeLabel(scan.created_at)}`),
        h("div", { class: "feature-meta" },
          h("span", {}, `${pagesLabel(scan.pages)} · ${sizeLabel(scan.size)}`),
          expiryEl(scan),
        ),
        h("div", { class: "feature-actions" },
          downloadButton(scan, "btn btn-primary btn-lg"),
          h("button", { class: "btn btn-secondary btn-lg", type: "button", onclick: () => openSend(scan) }, iconEl("send"), "Envoyer"),
          h("button", { class: "btn btn-ghost btn-lg", type: "button", onclick: () => openViewer(scan) }, iconEl("eye"), "Voir"),
        ),
      ),
    );
  }

  function card(scan, index) {
    const el = h("button", {
      class: `card${state.freshIds.has(scan.id) ? " fresh" : ""}`, type: "button",
      style: `animation-delay:${80 + index * 40}ms`, onclick: () => openViewer(scan),
      "aria-label": `${docTitle(scan)} du ${dayLabel(scan.created_at)} à ${timeLabel(scan.created_at)}`,
    },
      paper(scan, { stacked: scan.pages > 1 }),
      h("div", { class: "card-info" },
        h("span", { class: "card-title" }, `${dayLabel(scan.created_at)}, ${timeLabel(scan.created_at)}`),
        h("span", { class: "card-meta" }, scan.kind === "merge" ? `Fusion · ${pagesLabel(scan.pages)}` : `${pagesLabel(scan.pages)} · ${sizeLabel(scan.size)}`),
      ),
    );
    return el;
  }

  function selectableCard(scan, index) {
    const pos = state.selection.indexOf(scan.id);
    const el = h("button", {
      class: `card${pos >= 0 ? " selected" : ""}`, type: "button", "aria-pressed": pos >= 0 ? "true" : "false",
      style: `animation-delay:${index * 30}ms`,
      onclick: () => { toggleSelection(scan.id); },
    },
      h("span", { class: "select-mark" }, pos >= 0 ? String(pos + 1) : ""),
      paper(scan, { stacked: scan.pages > 1 }),
      h("div", { class: "card-info" },
        h("span", { class: "card-title" }, `${dayLabel(scan.created_at)}, ${timeLabel(scan.created_at)}`),
        h("span", { class: "card-meta" }, pagesLabel(scan.pages)),
      ),
    );
    return el;
  }

  function emptyState() {
    const address = state.info ? state.info.scan_address : "";
    return h("section", { class: "empty" },
      h("div", { class: "lock-mark", "aria-hidden": "true" }),
      h("h3", {}, "Aucun document pour l’instant"),
      h("p", {}, "Lancez une numérisation depuis l’imprimante. Elle s’affichera ici en quelques secondes, sans recharger la page."),
      h("div", { class: "steps" },
        h("span", {}, "Numériser"), iconEl("right"),
        h("span", {}, "E-mail"), iconEl("right"),
        h("span", {}, address),
      ),
    );
  }

  // ---------------------------------------------------------------- fusion
  function startMerge() {
    state.merging = true;
    state.selection = [];
    renderMain();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function stopMerge() {
    state.merging = false;
    state.selection = [];
    renderMain();
  }
  function toggleSelection(id) {
    const pos = state.selection.indexOf(id);
    if (pos >= 0) state.selection.splice(pos, 1);
    else state.selection.push(id);
    if (navigator.vibrate) navigator.vibrate(8);
    renderMain();
  }
  function moveSelection(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= state.selection.length) return;
    const list = state.selection;
    [list[index], list[target]] = [list[target], list[index]];
    renderMain();
  }

  function mergeTray() {
    const sel = state.selection;
    const list = h("div", { class: "tray-list" });
    if (!sel.length) list.append(h("div", { class: "tray-empty" }, "Aucun document sélectionné."));
    sel.forEach((id, i) => {
      const scan = byId(id);
      if (!scan) return;
      list.append(h("div", { class: "chip-doc", style: "animation:none" },
        h("button", { class: "icon-btn", type: "button", "aria-label": "Avancer", disabled: i === 0, html: icon("left"), onclick: () => moveSelection(i, -1) }),
        h("span", { class: "n" }, String(i + 1)),
        h("div", { class: "mini" }, h("img", { src: thumbUrl(scan), alt: "" })),
        h("button", { class: "icon-btn", type: "button", "aria-label": "Reculer", disabled: i === sel.length - 1, html: icon("right"), onclick: () => moveSelection(i, 1) }),
      ));
    });
    const pages = sel.reduce((n, id) => n + ((byId(id) || {}).pages || 0), 0);
    const create = h("button", { class: "btn btn-primary btn-lg", type: "button", disabled: sel.length < 2 },
      iconEl("layers"), "Créer le PDF");
    create.addEventListener("click", async () => {
      create.disabled = true;
      create.replaceChildren(h("span", { class: "spinner" }), "Assemblage…");
      try {
        const merged = await api("/api/merge", { method: "POST", body: { ids: sel } });
        state.merging = false;
        state.selection = [];
        await refresh();
        toast("PDF assemblé");
        openViewer(merged);
      } catch (err) {
        toast(err.message, "error");
        renderMain();
      }
    });
    const tray = h("div", { class: "tray", style: document.querySelector(".tray") ? "animation:none" : "" },
      list,
      h("div", { class: "tray-hint" }, sel.length < 2
        ? "Sélectionnez au moins 2 documents."
        : `${sel.length} documents · ${pagesLabel(pages)} · flèches pour changer l’ordre`),
      h("div", { class: "tray-actions" },
        h("button", { class: "btn btn-secondary btn-lg", type: "button", onclick: stopMerge }, "Annuler"),
        create,
      ),
    );
    return tray;
  }

  // ---------------------------------------------------------------- feuilles
  const sheets = [];
  function openSheet({ title, sub, body, foot, wide = false, onClose }) {
    const root = h("div", { class: "sheet-root", role: "dialog", "aria-modal": "true" });
    const close = () => {
      if (root.classList.contains("closing")) return;
      root.classList.add("closing");
      const i = sheets.indexOf(api);
      if (i >= 0) sheets.splice(i, 1);
      setTimeout(() => { root.remove(); if (!sheets.length) document.body.classList.remove("locked-scroll"); }, 280);
      if (onClose) onClose();
    };
    const head = h("div", { class: "sheet-head" },
      h("div", {}, h("h3", {}, title), sub ? h("div", { class: "sub" }, sub) : null),
      h("button", { class: "icon-btn", type: "button", "aria-label": "Fermer", html: icon("close"), onclick: close }),
    );
    const bodyEl = h("div", { class: "sheet-body" }, body);
    const sheet = h("div", { class: `sheet${wide ? " wide" : ""}` }, h("div", { class: "sheet-grip" }), head, bodyEl, foot ? h("div", { class: "sheet-foot" }, foot) : null);
    root.append(h("div", { class: "scrim", onclick: close }), sheet);
    document.body.append(root);
    document.body.classList.add("locked-scroll");
    const api = { root, sheet, body: bodyEl, close, setFoot: (nodes) => {
      let f = sheet.querySelector(".sheet-foot");
      if (!nodes) { if (f) f.remove(); return; }
      if (!f) { f = h("div", { class: "sheet-foot" }); sheet.append(f); }
      f.replaceChildren(...[].concat(nodes));
    } };
    sheets.push(api);
    return api;
  }
  function closeAllSheets() { [...sheets].forEach((s) => s.close()); }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheets.length) sheets[sheets.length - 1].close(); });

  // ---------------------------------------------------------------- aperçu
  function openViewer(scan) {
    const pages = h("div", { class: "viewer" });
    for (let i = 0; i < scan.pages; i++) {
      const img = h("img", { src: `/api/scans/${scan.id}/pages/${i}`, alt: `Page ${i + 1}`, loading: i < 2 ? "eager" : "lazy", decoding: "async" });
      img.addEventListener("load", () => img.classList.add("ready"));
      pages.append(h("div", { class: "paper" }, img));
      if (scan.pages > 1) pages.append(h("div", { class: "page-label" }, `${i + 1} / ${scan.pages}`));
    }
    const removeBtn = h("button", { class: "icon-btn", type: "button", "aria-label": "Supprimer", title: "Supprimer maintenant", html: icon("trash"), style: "color:var(--danger)" });
    const sheet = openSheet({
      title: `${dayLabel(scan.created_at)}, ${timeLabel(scan.created_at)}`,
      sub: `${scan.kind === "merge" ? "Document fusionné · " : ""}${pagesLabel(scan.pages)} · ${sizeLabel(scan.size)} · ${expiryLabel(scan.expires_at)}`,
      body: pages,
      wide: true,
      foot: [
        downloadButton(scan, "btn btn-primary btn-lg"),
        h("button", { class: "btn btn-secondary btn-lg", type: "button", onclick: () => openSend(scan) }, iconEl("send"), "Envoyer"),
        removeBtn,
      ],
    });
    removeBtn.addEventListener("click", () => confirmDelete(scan, sheet));
  }

  function confirmDelete(scan, parent) {
    const confirm = openSheet({
      title: "Supprimer ce document ?",
      sub: "Il sera effacé définitivement, sans attendre les 24 h.",
      body: h("div"),
      foot: [
        h("button", { class: "btn btn-secondary btn-lg", type: "button", onclick: () => confirm.close() }, "Annuler"),
        h("button", { class: "btn btn-primary btn-lg", type: "button", style: "background:var(--danger);color:#fff", onclick: async () => {
          try {
            await api(`/api/scans/${scan.id}`, { method: "DELETE" });
            confirm.close();
            if (parent) parent.close();
            toast("Document supprimé");
            await refresh();
          } catch (err) { toast(err.message, "error"); }
        } }, iconEl("trash"), "Supprimer"),
      ],
    });
  }

  // ---------------------------------------------------------------- envoi
  async function loadContacts() {
    if (!state.contacts) state.contacts = (await api("/api/contacts")).contacts;
    return state.contacts;
  }

  async function openSend(scan) {
    if (!state.canSend) { toast("L’envoi d’e-mails n’est pas configuré.", "error"); return; }
    let contacts = [];
    try { contacts = await loadContacts(); } catch (_) { /* liste vide */ }
    const selected = new Set();
    const extra = []; // adresses saisies

    const chips = h("div", { class: "chips" });
    const renderChips = () => {
      chips.replaceChildren();
      contacts.forEach((c) => {
        const on = selected.has(c.email);
        chips.append(h("button", { class: `chip${on ? " on" : ""}`, type: "button", "aria-pressed": on ? "true" : "false", onclick: () => { on ? selected.delete(c.email) : selected.add(c.email); renderChips(); } },
          h("span", { class: "avatar" }, on ? iconEl("check") : initials(c.name)), c.name, h("small", {}, c.email)));
      });
      extra.forEach((email) => {
        chips.append(h("button", { class: "chip on", type: "button", title: "Retirer", onclick: () => { extra.splice(extra.indexOf(email), 1); renderChips(); } },
          h("span", { class: "avatar" }, iconEl("at")), email, h("span", { html: icon("close", 'style="width:14px;height:14px;opacity:.7"') })));
      });
      if (!contacts.length && !extra.length) chips.append(h("div", { class: "hint" }, "Aucun contact enregistré. Saisissez une adresse ci-dessous."));
      updateButton();
    };

    const emailInput = h("input", { class: "input", type: "email", inputmode: "email", autocomplete: "email", placeholder: "nom@exemple.fr", "aria-label": "Adresse e-mail", autocapitalize: "off", spellcheck: "false" });
    const addBtn = h("button", { class: "btn btn-secondary", type: "button", "aria-label": "Ajouter l’adresse" }, iconEl("plus"), "Ajouter");
    const error = h("div", { class: "form-error" });
    const isEmail = (v) => /^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$/.test(v);
    const addTyped = () => {
      const value = emailInput.value.trim();
      if (!value) return true;
      if (!isEmail(value)) { error.textContent = "Cette adresse e-mail ne semble pas valide."; emailInput.focus(); return false; }
      error.textContent = "";
      const known = contacts.find((c) => c.email.toLowerCase() === value.toLowerCase());
      if (known) selected.add(known.email);
      else if (!extra.includes(value)) extra.push(value);
      emailInput.value = "";
      renderChips();
      return true;
    };
    addBtn.addEventListener("click", addTyped);
    emailInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addTyped(); } });
    emailInput.addEventListener("input", () => { error.textContent = ""; updateButton(); });

    const remember = h("input", { type: "checkbox" });
    const message = h("textarea", { class: "textarea", placeholder: "Bonjour, voici le document…", "aria-label": "Message" });

    const sendBtn = h("button", { class: "btn btn-primary btn-lg", type: "button" });
    function updateButton() {
      const typed = isEmail(emailInput.value.trim()) ? 1 : 0;
      const n = selected.size + extra.length + typed;
      sendBtn.disabled = n === 0;
      sendBtn.replaceChildren(iconEl("send"), n > 1 ? `Envoyer à ${n} destinataires` : "Envoyer");
    }

    const body = h("div", {},
      h("div", { class: "field" }, h("span", { class: "label" }, contacts.length ? "Envoi rapide" : "Destinataires"), chips),
      h("div", { class: "field" },
        h("label", {}, "Autre adresse"),
        h("div", { class: "input-row" }, emailInput, addBtn),
        error,
        h("label", { class: "check" }, remember, "Enregistrer les nouvelles adresses dans mes contacts"),
      ),
      h("div", { class: "field" }, h("label", {}, "Message ", h("span", { class: "hint" }, "(facultatif)")), message),
    );

    const sheet = openSheet({
      title: "Envoyer par e-mail",
      sub: `${docTitle(scan)} · ${dayLabel(scan.created_at)}, ${timeLabel(scan.created_at)} · ${pagesLabel(scan.pages)}`,
      body,
      foot: [sendBtn],
    });
    renderChips();

    sendBtn.addEventListener("click", async () => {
      if (!addTyped()) return;
      const recipients = [...selected, ...extra];
      if (!recipients.length) return;
      sendBtn.disabled = true;
      sendBtn.replaceChildren(h("span", { class: "spinner" }), "Envoi en cours…");
      try {
        await api(`/api/scans/${scan.id}/send`, { method: "POST", body: { recipients, message: message.value } });
        if (remember.checked && extra.length) {
          for (const email of extra) {
            try { await api("/api/contacts", { method: "POST", body: { name: email.split("@")[0], email } }); } catch (_) { /* ignoré */ }
          }
          state.contacts = null;
        }
        sheet.body.replaceChildren(h("div", { class: "done" },
          h("div", { class: "done-mark", html: icon("check", 'stroke-width="2.2"') }),
          h("h3", {}, "Envoyé"),
          h("p", {}, recipients.length > 1 ? `Le document a été envoyé à ${recipients.length} destinataires.` : `Le document a été envoyé à ${recipients[0]}.`),
        ));
        sheet.setFoot([h("button", { class: "btn btn-secondary btn-lg btn-block", type: "button", onclick: () => sheet.close() }, "Terminé")]);
      } catch (err) {
        toast(err.message, "error");
        updateButton();
      }
    });
  }

  // ---------------------------------------------------------------- réglages
  async function openSettings() {
    const contactList = h("div", { class: "list" });
    const renderContacts = async () => {
      let contacts = [];
      try { state.contacts = null; contacts = await loadContacts(); } catch (_) { /* vide */ }
      contactList.replaceChildren();
      if (!contacts.length) contactList.append(h("div", { class: "list-empty" }, "Aucun contact pour le moment."));
      contacts.forEach((c) => contactList.append(h("div", { class: "list-row" },
        h("span", { class: "chip", style: "border:0;padding:0;min-height:0;background:none" }, h("span", { class: "avatar" }, initials(c.name))),
        h("div", { class: "grow" }, h("div", { class: "t" }, c.name), h("div", { class: "s" }, c.email)),
        h("button", { class: "icon-btn", type: "button", "aria-label": `Supprimer ${c.name}`, html: icon("trash"), onclick: async () => {
          try { await api(`/api/contacts/${c.id}`, { method: "DELETE" }); await renderContacts(); } catch (err) { toast(err.message, "error"); }
        } }),
      )));
    };

    const cName = h("input", { class: "input", placeholder: "Nom (ex. Comptable)", "aria-label": "Nom", autocomplete: "off" });
    const cEmail = h("input", { class: "input", type: "email", inputmode: "email", placeholder: "adresse@exemple.fr", "aria-label": "E-mail", autocapitalize: "off", spellcheck: "false" });
    const cError = h("div", { class: "form-error" });
    const cAdd = h("button", { class: "btn btn-secondary btn-block", type: "submit" }, iconEl("plus"), "Ajouter le contact");
    const contactForm = h("form", { style: "display:grid;gap:10px;margin-top:14px" }, cName, cEmail, cError, cAdd);
    contactForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      cError.textContent = "";
      try {
        await api("/api/contacts", { method: "POST", body: { name: cName.value, email: cEmail.value.trim() } });
        cName.value = ""; cEmail.value = "";
        await renderContacts();
        toast("Contact ajouté");
      } catch (err) { cError.textContent = err.message; }
    });

    const pCurrent = h("input", { class: "input", type: "password", autocomplete: "current-password", placeholder: "Code actuel", "aria-label": "Code actuel" });
    const pNew = h("input", { class: "input", type: "password", autocomplete: "new-password", placeholder: "Nouveau code", "aria-label": "Nouveau code" });
    const pConfirm = h("input", { class: "input", type: "password", autocomplete: "new-password", placeholder: "Confirmez le nouveau code", "aria-label": "Confirmation" });
    const pError = h("div", { class: "form-error" });
    const pinForm = h("form", { style: "display:grid;gap:10px" }, pCurrent, pNew, pConfirm, pError,
      h("button", { class: "btn btn-secondary btn-block", type: "submit" }, "Changer le code"));
    pinForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      pError.textContent = "";
      if (!pNew.value) { pError.textContent = "Saisissez un nouveau code."; return; }
      if (pNew.value !== pConfirm.value) { pError.textContent = "Les deux nouveaux codes ne correspondent pas."; return; }
      try {
        await api("/api/pin", { method: "POST", body: { current: pCurrent.value, new: pNew.value } });
        pCurrent.value = pNew.value = pConfirm.value = "";
        toast("Code modifié");
      } catch (err) { pError.textContent = err.message; }
    });

    openSheet({
      title: "Réglages",
      body: h("div", {},
        h("section", { class: "settings-section" },
          h("h4", {}, "Contacts favoris"),
          h("p", {}, "Ils apparaissent en un geste au moment d’envoyer un document."),
          contactList, contactForm),
        h("div", { class: "divider" }),
        h("section", { class: "settings-section" },
          h("h4", {}, "Apparence"),
          h("p", {}, "Le mode sombre est utilisé par défaut. Ce choix est mémorisé sur cet appareil."),
          themePicker()),
        h("div", { class: "divider" }),
        h("section", { class: "settings-section" },
          h("h4", {}, "Code d’accès"),
          h("p", {}, "Aucune contrainte de longueur : chiffres, lettres, phrase…"),
          pinForm),
        h("div", { class: "divider" }),
        h("button", { class: "btn btn-ghost btn-block", type: "button", onclick: logout }, iconEl("lock"), "Verrouiller maintenant"),
      ),
    });
    renderContacts();
  }

  function themePicker() {
    const options = [["dark", "moon", "Sombre"], ["light", "sun", "Clair"], ["auto", "auto", "Auto"]];
    const group = h("div", { class: "segmented", role: "group", "aria-label": "Thème" });
    const render = () => {
      const current = window.ScanTheme ? window.ScanTheme.get() : "dark";
      group.replaceChildren(...options.map(([value, ico, label]) => h("button", {
        type: "button", "aria-pressed": value === current ? "true" : "false",
        onclick: () => { if (window.ScanTheme) window.ScanTheme.set(value); render(); },
      }, iconEl(ico), label)));
    };
    render();
    return group;
  }

  async function logout() {
    try { await api("/api/logout", { method: "POST" }); } catch (_) { /* ignoré */ }
    state.contacts = null;
    lockApp();
  }

  // ---------------------------------------------------------------- défilement
  window.addEventListener("scroll", () => {
    const bar = document.querySelector(".topbar");
    if (bar) bar.classList.toggle("scrolled", window.scrollY > 8);
  }, { passive: true });

  // ---------------------------------------------------------------- démarrage
  (async () => {
    try {
      state.info = await api("/api/session");
      if (state.info.authenticated) await enterApp();
      else renderLock();
    } catch (_) {
      renderLock("Serveur injoignable. Réessayez dans un instant.");
    }
  })();
})();
