/* AUTO-GENERATED from ts/app/app-help/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/app-help/auto-mount.ts --bundle --format=esm --outfile=js/app/app-help.js */
// ts/_base/gettext.ts
var JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-";
var state = null;
function installCatalog(payload) {
  const current = state ?? { entries: {}, plural: null };
  state = {
    entries: { ...current.entries, ...payload.catalog },
    plural: payload.plural ?? current.plural
  };
}
function loadCatalogsFromDocument(doc) {
  const elements = doc.querySelectorAll(
    `script[type="application/json"][id^="${JS_CATALOG_ELEMENT_PREFIX}"]`
  );
  for (const element of Array.from(elements)) {
    installCatalog(JSON.parse(element.textContent || "{}"));
  }
}
function activeCatalog() {
  if (state === null) {
    state = { entries: {}, plural: null };
    if (typeof document !== "undefined") loadCatalogsFromDocument(document);
  }
  return state;
}
function gettext(msgid) {
  const entry = activeCatalog().entries[msgid];
  if (entry === void 0) return msgid;
  const translated = typeof entry === "string" ? entry : entry[0];
  return translated || msgid;
}

// ts/app/app-help/_AppHelp.ts
var HELP_ATTRIBUTE = "data-stx-help";
var HELP_CHANGE = "stx-app-help:change";
var STORAGE_PREFIX = "stx-help:";
var SCRIPT_ID_PREFIX = "stx-app-help-";
var CLS = "stx-app-help";
var CLS_BUTTON = `${CLS}__button`;
var CLS_PANEL = `${CLS}__panel`;
var CLS_PANEL_BODY = `${CLS}__panel-body`;
var CLS_TOUR = `${CLS}__tour`;
var CLS_TOUR_BUBBLE = `${CLS}__tour-bubble`;
var CLS_TOUR_HIGHLIGHT = `${CLS}__tour-highlight`;
var CLS_STEP = `${CLS}__step`;
var CLS_STEP_ICON = `${CLS}__step-icon`;
var CLS_STEP_TITLE = `${CLS}__step-title`;
var CLS_STEP_BODY = `${CLS}__step-body`;
var CLS_CLOSE = `${CLS}__close`;
var CLS_COUNT = `${CLS}__count`;
var CLS_NAV = `${CLS}__nav`;
var CLS_CHOICES = `${CLS}__choices`;
var CLS_CHOICE = `${CLS}__choice`;
var CLS_ENTRY = `${CLS}__tour-entry`;
function activeLanguage(doc = document) {
  const lang = doc.documentElement?.getAttribute("lang")?.toLowerCase() ?? "";
  const base = lang.split("-")[0] || "en";
  return base;
}
function stepText(text, lang) {
  if (text === void 0) return "";
  if (typeof text === "string") return gettext(text);
  return gettext(text[lang] ?? text.en ?? "");
}
function slug(value) {
  return value.replace(/[^A-Za-z0-9_-]+/g, "-");
}
function defaultStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}
function loadGuide(app, doc = document) {
  const script = doc.getElementById(`${SCRIPT_ID_PREFIX}${slug(app)}`);
  if (!script || !script.textContent) return null;
  try {
    const data = JSON.parse(script.textContent);
    if (!data || !Array.isArray(data.steps)) return null;
    return data;
  } catch {
    return null;
  }
}
var AppHelp = class {
  root;
  app;
  guide;
  language;
  storage;
  steps;
  tourSteps;
  button;
  panel = null;
  tour = null;
  highlight = null;
  tourIndex = 0;
  constructor(root, options = {}) {
    this.root = root;
    this.app = options.app || root.getAttribute(HELP_ATTRIBUTE) || "default";
    this.language = options.language || activeLanguage();
    this.storage = options.storage === void 0 ? defaultStorage() : options.storage;
    this.guide = loadGuide(this.app) ?? { app: this.app, steps: [] };
    this.steps = this.guide.steps;
    this.tourSteps = this.steps.filter((s) => typeof s.target === "string" && s.target !== "");
    root.classList.add(CLS);
    this.button = this.renderButton();
    root.appendChild(this.button);
    if (options.autoStart === false) return;
    if (this.tourPreference() === "unseen" && !this.firstOpenDone() && this.tourSteps.length > 0) {
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(() => this.showTourInvite());
      } else {
        this.showTourInvite();
      }
    }
  }
  get open() {
    return this.panel !== null;
  }
  /** True once the user has completed or dismissed the first-open tour. */
  firstOpenDone() {
    try {
      return this.storage?.getItem(`${STORAGE_PREFIX}${this.app}:done`) === "1";
    } catch {
      return true;
    }
  }
  /**
   * What the user answered at first use: "unseen" | "later" | "never".
   *
   * A SEPARATE KEY FROM `done` on purpose. `done` records that the guide was
   * SEEN (a fact about the guide); this records what the user ASKED FOR (a fact
   * about the user). Overwriting one with the other is how "Later" becomes
   * indistinguishable from "Do not show again", and how a primitive ends up
   * either re-offering a tour to someone who refused it or dropping it for
   * someone who only postponed it.
   */
  tourPreference() {
    try {
      const stored = this.storage?.getItem(this.tourKey());
      return stored === "later" || stored === "never" ? stored : "unseen";
    } catch {
      return "unseen";
    }
  }
  /** "Later": not now, and not a refusal. Suppresses the auto-start. */
  deferTour() {
    this.writeTourPreference("later");
    this.closeTour();
    this.emit({ view: "closed", choice: "later" });
  }
  /** "Do not show again": a refusal. Reversible only through reset. */
  dismissTourForever() {
    this.writeTourPreference("never");
    this.closeTour();
    this.emit({ view: "closed", choice: "never" });
  }
  /**
   * Drop both the preference and the seen-flag, so Settings can re-offer the
   * tour (SSOT: "reversible in Settings"). Deliberately clearing `done` too:
   * a user who resets wants the tour offered again.
   */
  resetTourPreference() {
    try {
      this.storage?.removeItem(this.tourKey());
      this.storage?.removeItem(`${STORAGE_PREFIX}${this.app}:done`);
    } catch {
    }
    this.emit({ view: "closed", choice: "watch" });
  }
  tourKey() {
    return `${STORAGE_PREFIX}${this.app}:tour`;
  }
  writeTourPreference(preference) {
    try {
      this.storage?.setItem(this.tourKey(), preference);
    } catch {
    }
  }
  markFirstOpenDone() {
    try {
      this.storage?.setItem(`${STORAGE_PREFIX}${this.app}:done`, "1");
    } catch {
    }
  }
  /** Open the `?` help panel. */
  openPanel() {
    if (this.panel) return;
    this.closeTour();
    this.panel = this.renderPanel();
    this.root.appendChild(this.panel);
    this.emit({ view: "panel" });
    const closeBtn = this.panel.querySelector(`.${CLS_CLOSE}`);
    closeBtn?.focus();
  }
  closePanel() {
    if (!this.panel) return;
    this.panel.remove();
    this.panel = null;
    this.emit({ view: "closed" });
  }
  /** Open or close the panel (the `?` button behavior). */
  toggle() {
    if (this.panel) this.closePanel();
    else this.openPanel();
  }
  /** Start the first-open coach-mark tour from the beginning. */
  startTour() {
    if (this.tourSteps.length === 0) return;
    this.closePanel();
    this.tourIndex = 0;
    if (!this.tour) {
      this.tour = this.renderTour();
      this.root.appendChild(this.tour);
    }
    this.showTourStep(0);
    this.emit({ view: "tour", step: 0 });
  }
  /**
   * Show the first-use invite: the tour bubble with the three choices and no
   * highlight, so nothing is pointed at until the user asks to watch.
   */
  showTourInvite() {
    this.closePanel();
    if (!this.tour) {
      this.tour = this.renderTour();
      this.root.appendChild(this.tour);
    }
    const entry = this.tour.querySelector(`.${CLS_ENTRY}`);
    if (entry) {
      entry.innerHTML = `<div class="${CLS_STEP}"><div class="${CLS_STEP_TITLE}">${gettext(
        "Take a quick tour?"
      )}</div></div>`;
    }
    this.setChoicesVisible(true);
    this.emit({ view: "tour", step: 0 });
  }
  /** Replay the tour (available from the panel footer). */
  replayTour() {
    this.startTour();
  }
  closeTour() {
    if (!this.tour) return;
    this.tour.remove();
    this.tour = null;
    this.highlight?.remove();
    this.highlight = null;
    this.markFirstOpenDone();
    this.emit({ view: "closed" });
  }
  nextTourStep() {
    if (this.tourIndex < this.tourSteps.length - 1) {
      this.showTourStep(this.tourIndex + 1);
      this.emit({ view: "tour", step: this.tourIndex });
    } else {
      this.closeTour();
    }
  }
  prevTourStep() {
    if (this.tourIndex > 0) {
      this.showTourStep(this.tourIndex - 1);
      this.emit({ view: "tour", step: this.tourIndex });
    }
  }
  showTourStep(index) {
    this.tourIndex = index;
    const step = this.tourSteps[index];
    if (!this.tour) return;
    const target = step.target ? document.querySelector(step.target) : null;
    if (this.highlight) this.highlight.remove();
    if (target) {
      this.highlight = document.createElement("div");
      this.highlight.className = CLS_TOUR_HIGHLIGHT;
      const rect = target.getBoundingClientRect();
      Object.assign(this.highlight.style, {
        position: "fixed",
        left: `${rect.left - 4}px`,
        top: `${rect.top - 4}px`,
        width: `${rect.width + 8}px`,
        height: `${rect.height + 8}px`
      });
      this.root.appendChild(this.highlight);
    }
    const entry = this.tour.querySelector(`.${CLS_ENTRY}`);
    if (entry) {
      const icon = step.icon ? `<span class="${CLS_STEP_ICON}" aria-hidden="true">${step.icon}</span>` : "";
      const title = stepText(step.title, this.language) || gettext("Guide");
      const body = stepText(step.body, this.language);
      entry.innerHTML = `<div class="${CLS_STEP}">${icon}<div class="${CLS_STEP_TITLE}">${title}</div>` + (body ? `<div class="${CLS_STEP_BODY}">${body}</div>` : "") + `</div>`;
    }
    this.setChoicesVisible(false);
    const count = this.tour.querySelector(`.${CLS_COUNT}`);
    if (count) count.textContent = `${index + 1} / ${this.tourSteps.length}`;
    const nav = this.tour.querySelector(`.${CLS_NAV}`);
    if (nav) {
      const prev = nav.querySelector('[data-act="prev"]');
      if (prev) prev.disabled = index === 0;
      const next = nav.querySelector('[data-act="next"]');
      if (next) next.textContent = index === this.tourSteps.length - 1 ? gettext("Done") : gettext("Next");
    }
  }
  /**
   * The three first-use choices, each wired to its own outcome.
   * Labels are translated; the `--watch/--later/--never` hooks are not, so a
   * leaf can target one answer without matching on prose that changes per
   * language.
   */
  renderChoices() {
    const wrap = document.createElement("div");
    wrap.className = CLS_CHOICES;
    const choices = [
      ["watch", gettext("Watch tour")],
      ["later", gettext("Later")],
      ["never", gettext("Do not show again")]
    ];
    for (const [choice, label] of choices) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `${CLS_CHOICE} ${CLS_CHOICE}--${choice}`;
      button.dataset.choice = choice;
      button.textContent = label;
      button.addEventListener("click", () => {
        if (choice === "watch") {
          this.startTour();
          this.emit({ view: "tour", step: 0, choice });
        } else if (choice === "later") {
          this.deferTour();
        } else {
          this.dismissTourForever();
        }
      });
      wrap.appendChild(button);
    }
    return wrap;
  }
  /** The choices belong to the invite, not to every step of a running tour. */
  setChoicesVisible(visible) {
    const choices = this.tour?.querySelector(`.${CLS_CHOICES}`);
    if (choices) choices.hidden = !visible;
  }
  renderButton() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = CLS_BUTTON;
    button.setAttribute("aria-label", gettext("How to use"));
    button.setAttribute("data-stx-help-open", "");
    button.textContent = "?";
    button.addEventListener("click", () => this.toggle());
    return button;
  }
  renderPanel() {
    const panel = document.createElement("div");
    panel.className = CLS_PANEL;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", gettext("How to use"));
    const header = document.createElement("div");
    header.className = `${CLS}__header`;
    const title = document.createElement("h3");
    title.className = `${CLS}__title`;
    title.textContent = gettext("How to use");
    const close = document.createElement("button");
    close.type = "button";
    close.className = CLS_CLOSE;
    close.setAttribute("aria-label", gettext("Close"));
    close.textContent = "\xD7";
    close.addEventListener("click", () => this.closePanel());
    header.append(title, close);
    panel.appendChild(header);
    const body = document.createElement("div");
    body.className = CLS_PANEL_BODY;
    this.steps.forEach((step, i) => {
      const item = document.createElement("div");
      item.className = CLS_STEP;
      const icon = step.icon ? `<span class="${CLS_STEP_ICON}" aria-hidden="true">${step.icon}</span>` : "";
      const num = `<span class="${CLS}__step-num" aria-hidden="true">${i + 1}</span>`;
      const title2 = stepText(step.title, this.language);
      const bodyText = stepText(step.body, this.language);
      item.innerHTML = `${num}${icon}<div class="${CLS}__step-text">` + (title2 ? `<div class="${CLS_STEP_TITLE}">${title2}</div>` : "") + (bodyText ? `<div class="${CLS_STEP_BODY}">${bodyText}</div>` : "") + `</div>`;
      body.appendChild(item);
    });
    panel.appendChild(body);
    const footer = document.createElement("div");
    footer.className = `${CLS}__footer`;
    const replay = document.createElement("button");
    replay.type = "button";
    replay.className = `${CLS}__replay`;
    replay.textContent = gettext("Replay the tour");
    replay.addEventListener("click", () => this.replayTour());
    footer.appendChild(replay);
    panel.appendChild(footer);
    const onKey = (e) => {
      if (e.key === "Escape") {
        this.closePanel();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);
    return panel;
  }
  renderTour() {
    const tour = document.createElement("div");
    tour.className = CLS_TOUR;
    tour.setAttribute("role", "dialog");
    tour.setAttribute("aria-modal", "true");
    tour.setAttribute("aria-label", gettext("How to use"));
    const bubble = document.createElement("div");
    bubble.className = CLS_TOUR_BUBBLE;
    const entry = document.createElement("div");
    entry.className = CLS_ENTRY;
    bubble.appendChild(entry);
    bubble.appendChild(this.renderChoices());
    this.setChoicesVisible(false);
    tour.appendChild(bubble);
    const meta = document.createElement("div");
    meta.className = `${CLS}__tour-meta`;
    const count = document.createElement("span");
    count.className = CLS_COUNT;
    const nav = document.createElement("div");
    nav.className = CLS_NAV;
    const prev = document.createElement("button");
    prev.type = "button";
    prev.dataset.act = "prev";
    prev.textContent = gettext("Back");
    const next = document.createElement("button");
    next.type = "button";
    next.dataset.act = "next";
    next.textContent = gettext("Next");
    const skip = document.createElement("button");
    skip.type = "button";
    skip.dataset.act = "skip";
    skip.textContent = gettext("Skip");
    nav.append(prev, next, skip);
    meta.append(count, nav);
    tour.appendChild(meta);
    prev.addEventListener("click", () => this.prevTourStep());
    next.addEventListener("click", () => this.nextTourStep());
    skip.addEventListener("click", () => this.closeTour());
    return tour;
  }
  emit(detail) {
    const full = { app: this.app, ...detail };
    this.root.dispatchEvent(new CustomEvent(HELP_CHANGE, { detail: full, bubbles: true }));
  }
  /** Remove all rendered help chrome (SPA teardown). */
  destroy() {
    this.panel?.remove();
    this.tour?.remove();
    this.highlight?.remove();
    this.panel = null;
    this.tour = null;
    this.highlight = null;
  }
};

// ts/app/app-help/mount.ts
var MOUNTED_ATTRIBUTE = "data-stx-help-mounted";
var instances = [];
function mountAppHelp(root = document, options = {}) {
  const mounted = [];
  for (const element of Array.from(root.querySelectorAll(`[${HELP_ATTRIBUTE}]`))) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const help = new AppHelp(element, options);
    instances.push(help);
    mounted.push(help);
  }
  return mounted;
}
function getAppHelp(app) {
  if (app) return instances.find((item) => item.app === app) ?? null;
  return instances.length === 1 ? instances[0] : null;
}
function openHelp(app) {
  getAppHelp(app)?.openPanel();
}
function closeHelp(app) {
  getAppHelp(app)?.closePanel();
}
function replayHelp(app) {
  getAppHelp(app)?.replayTour();
}
var stxHelp = {
  mount: mountAppHelp,
  get: getAppHelp,
  open: openHelp,
  close: closeHelp,
  replay: replayHelp
};

// ts/app/app-help/auto-mount.ts
window.stxHelp = stxHelp;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountAppHelp());
} else {
  mountAppHelp();
}
export {
  AppHelp,
  HELP_ATTRIBUTE,
  HELP_CHANGE,
  SCRIPT_ID_PREFIX,
  STORAGE_PREFIX,
  activeLanguage,
  loadGuide,
  stepText
};
