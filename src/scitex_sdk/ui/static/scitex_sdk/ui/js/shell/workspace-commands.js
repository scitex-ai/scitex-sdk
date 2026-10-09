/* AUTO-GENERATED from ts/shell/workspace-commands/index.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/shell/workspace-commands.js */

// ts/_base/BaseComponent.ts
var BaseComponent = class {
  container;
  config;
  constructor(config) {
    this.config = config;
    const el = typeof config.container === "string" ? document.querySelector(config.container) : config.container;
    if (!el) {
      throw new Error(
        `${this.constructor.name}: container not found: ${config.container}`
      );
    }
    this.container = el;
  }
  /** Emit a custom event on the container. */
  emit(name, detail) {
    this.container.dispatchEvent(
      new CustomEvent(name, { detail, bubbles: true })
    );
  }
  /** Destroy the component and clean up DOM. */
  destroy() {
    this.container.innerHTML = "";
  }
};

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

// ts/shell/keymap/_registry.ts
var CommandRegistry = class {
  commands = /* @__PURE__ */ new Map();
  /** The active page/app mode, or null when none is active (global only). */
  mode = null;
  /** Register or REPLACE a command. Returns false when the ID is taken by a
   *  DIFFERENT definition (a re-registration with the same ID is allowed —
   *  it is how an app updates its own command without clearing the world). */
  set(def) {
    const existing = this.commands.get(def.id);
    if (existing && existing !== def) {
      this.commands.set(def.id, def);
      return false;
    }
    this.commands.set(def.id, def);
    return true;
  }
  /** Unregister by ID. Returns true if something was removed. */
  unset(id) {
    return this.commands.delete(id);
  }
  /** True if a command with this ID is registered (regardless of mode). */
  has(id) {
    return this.commands.has(id);
  }
  /** Look up a command, reporting whether it is active in the current mode. */
  get(id) {
    const def = this.commands.get(id);
    if (!def) return null;
    return { def, active: this.isActive(def) };
  }
  /** All registered command IDs, sorted — a stable introspection surface. */
  ids() {
    return [...this.commands.keys()].sort();
  }
  /**
   * The full introspection model for the help UI / agent: every command with
   * its label, group, current-mode activeness, and the bindings that point at
   * it (resolved by the caller, since bindings live in the Keymap, not here).
   */
  list() {
    return this.ids().map((id) => {
      const def = this.commands.get(id);
      return {
        id,
        label: def.label,
        group: def.group,
        active: this.isActive(def),
        modes: def.modes ? [...def.modes].sort() : null
      };
    });
  }
  /** Activate a page/app mode. Global commands stay active; mode-scoped
   *  commands become active only when their mode matches. */
  setMode(mode) {
    this.mode = mode;
  }
  get currentMode() {
    return this.mode;
  }
  isActive(def) {
    if (!def.modes) return true;
    return this.mode !== null && def.modes.has(this.mode);
  }
  run(id, ...dispatch) {
    const def = this.commands.get(id);
    if (!def || !this.isActive(def)) return false;
    const consumed = def.action(dispatch[1]);
    return consumed !== false;
  }
};
var globalRegistry = new CommandRegistry();

// ts/shell/keymap/_chords.ts
var MOD_TOKENS = {
  C: "ctrl",
  M: "alt",
  S: "shift",
  M2: "meta"
};
var NAMED_KEYS = {
  ret: "return",
  return: "return",
  enter: "return",
  tab: "tab",
  spac: " ",
  space: " ",
  esc: "escape",
  escape: "escape",
  up: "up",
  dwn: "down",
  down: "down",
  lft: "left",
  left: "left",
  rgt: "right",
  right: "right",
  del: "delete",
  delete: "delete",
  pgup: "pageup",
  pgdn: "pagedown",
  beg: "home",
  home: "home",
  end: "end"
};
function bareKey(token) {
  const named = NAMED_KEYS[token.toLowerCase()];
  if (named !== void 0) return named;
  return token.length === 1 ? token.toLowerCase() : token;
}
function parseChord(input) {
  const chord = { ctrl: false, alt: false, shift: false, meta: false, key: "" };
  const trimmed = input.trim();
  if (trimmed === "") throw new Error("parseChord: empty chord");
  let rest = trimmed;
  for (; ; ) {
    let matched = false;
    for (const token of ["M2", "C", "M", "S"]) {
      const needle = token + "-";
      if (rest.startsWith(needle)) {
        chord[MOD_TOKENS[token]] = true;
        rest = rest.slice(needle.length);
        matched = true;
        break;
      }
    }
    if (!matched) break;
  }
  chord.key = bareKey(rest);
  if (chord.key === "") throw new Error(`parseChord: no key in ${input}`);
  return chord;
}
function parseSequence(input) {
  return input.trim().split(/\s+/).filter(Boolean).map(parseChord);
}
function chordToString(chord) {
  const parts = [];
  if (chord.ctrl) parts.push("C");
  if (chord.alt) parts.push("M");
  if (chord.shift) parts.push("S");
  if (chord.meta) parts.push("M2");
  const key = chord.key.length === 1 && /[a-z0-9]/.test(chord.key) ? chord.key.toUpperCase() : chord.key;
  parts.push(key);
  return parts.join("-");
}
function sequenceKey(seq) {
  return seq.map(chordToString).join(" ");
}
function eventToChord(event) {
  const raw = event.key;
  if (raw === "Unidentified") return null;
  if (["Shift", "Control", "Alt", "Meta", "CapsLock"].includes(raw)) return null;
  const named = NAMED_KEYS[raw.toLowerCase()];
  const isLetter = /^[a-zA-Z]$/.test(raw);
  const key = named !== void 0 ? named : isLetter ? raw.toLowerCase() : raw;
  return {
    ctrl: event.ctrlKey,
    alt: event.altKey,
    shift: event.shiftKey,
    meta: event.metaKey,
    key
  };
}

// ts/shell/keymap/_keymap.ts
var INPUT_SELECTOR = "input, textarea, select, [contenteditable=''], [contenteditable='true'], [contenteditable='plaintext-only']";
var Keymap = class {
  registry;
  /** SOURCE OF TRUTH: the factory bindings the app adds via bind(), per scope.
   *  User overrides never mutate this — they are an overlay (overrideStorage /
   *  unbound) applied on top during rebuildEffective(). "global" is always
   *  present. */
  defaults = /* @__PURE__ */ new Map();
  /** The user override overlay: commandId -> the chord it now runs on. */
  overrideStorage;
  /** Command IDs the user has disabled. A disabled command keeps its factory
   *  default (so enable()/resetOverrides() restore exactly what was there) but
   *  contributes no effective chord while disabled. */
  unbound = /* @__PURE__ */ new Set();
  /** Override-induced collisions (an override landed on another command's
   *  effective chord). Surfaced via overrideConflicts() — never silent. */
  overrideCollisions = [];
  /** EFFECTIVE state (defaults + overrides − unbound): scope -> bindings.
   *  resolve/findBindingByChord/help read THIS, and it is rebuilt by
   *  rebuildEffective() after every mutation. */
  bindings = /* @__PURE__ */ new Map();
  /** EFFECTIVE state: scope -> canonical-sequence-key -> commandId (O(1) + conflicts). */
  index = /* @__PURE__ */ new Map();
  /** Pending prefix sequence while a multi-chord command is being typed. */
  pending = [];
  composing = false;
  // Typed as Event (not KeyboardEvent) so it satisfies addEventListener's
  // EventListener signature; handleKeydown duck-types the keyboard fields.
  onKeydown;
  onCompositionStart;
  onCompositionEnd;
  constructor(options = {}) {
    this.registry = options.registry ?? globalRegistry;
    this.overrideStorage = options.overrideStorage ?? /* @__PURE__ */ new Map();
    this.defaults.set("global", []);
    this.onKeydown = (event) => this.handleKeydown(event);
    this.onCompositionStart = () => {
      this.composing = true;
      this.resetPending();
    };
    this.onCompositionEnd = () => {
      this.composing = false;
      this.resetPending();
    };
    this.rebuildEffective();
  }
  /** The registry this keymap dispatches into, for consumer identity checks. */
  get commands() {
    return this.registry;
  }
  get currentMode() {
    return this.registry.currentMode;
  }
  /** Factory presence survives overrides, mode shadowing and user disabling. */
  hasFactoryBinding(commandId) {
    return [...this.defaults.values()].some(
      (bindings) => bindings.some((binding) => binding.commandId === commandId)
    );
  }
  /** Activate a page/app mode. Installs the scope so it is bindable, and
   *  tells the registry which mode-scoped commands are now live. */
  activateMode(mode) {
    this.ensureScope(mode);
    this.registry.setMode(mode);
    this.resetPending();
  }
  /** Return to global-only. Mode-scoped commands go inactive. */
  deactivateMode() {
    this.registry.setMode(null);
    this.resetPending();
  }
  /** Ensure a (non-global) scope exists in the defaults table so it is bindable. */
  ensureScope(scope) {
    if (scope !== "global" && !this.defaults.has(scope)) {
      this.defaults.set(scope, []);
    }
  }
  /** Bind a chord (or "C-x C-s" sequence) to a command ID in a scope.
   *  Returns a Conflict when the chord is already EFFECTIVELY bound to a
   *  DIFFERENT command in that scope — the authoring app decides what to do.
   *  Re-binding the same chord to the same command is a no-op, not a conflict.
   *  The conflict check reads the effective index, so a chord that is live
   *  only because of a user override counts as occupied. */
  bind(scope, sequenceStr, commandId, inInput = false) {
    this.ensureScope(scope);
    const seq = parseSequence(sequenceStr);
    const key = sequenceKey(seq);
    const existing = this.index.get(scope)?.get(key);
    if (existing !== void 0 && existing !== commandId) {
      return { sequenceKey: key, scope, existingCommandId: existing, newCommandId: commandId };
    }
    if (existing === commandId) return null;
    this.defaults.get(scope).push({ sequence: seq, commandId, inInput });
    this.rebuildEffective();
    return null;
  }
  /**
   * Apply a user override: remember that `sequenceStr` now runs `commandId`
   * instead of its default chord, in every scope where the command is bound.
   * The override is real state — rebuildEffective() runs immediately, so
   * keyboard + program dispatch and help() all change. Persist it with
   * serializeOverrides() / loadOverrides() (a Hub settings UI stores exactly
   * that JSON). The displaced default chord is freed (native behavior returns
   * to it) and, if the new chord was occupied by another command, the
   * collision is surfaced via overrideConflicts().
   */
  setOverride(commandId, sequenceStr) {
    this.overrideStorage.set(commandId, parseSequence(sequenceStr));
    this.rebuildEffective();
  }
  /**
   * Disable a command: it contributes no effective chord while disabled, but
   * its factory default is PRESERVED (so enable()/resetOverrides() restore
   * exactly what was there, not a rebuilt guess). Any override on it is
   * dropped — a disabled command has no chord to override.
   */
  unbind(commandId) {
    this.unbound.add(commandId);
    this.overrideStorage.delete(commandId);
    this.rebuildEffective();
  }
  /** Re-enable a previously disabled command at its factory default chord. */
  enable(commandId) {
    this.unbound.delete(commandId);
    this.rebuildEffective();
  }
  /** Reset every user override AND every unbind; factory defaults restored. */
  resetOverrides() {
    this.overrideStorage.clear();
    this.unbound.clear();
    this.rebuildEffective();
  }
  /**
   * Serialize the user's override state to pure JSON — the persistence
   * adapter's contract. `overrides` is commandId -> effective chord string
   * (canonical display form, e.g. "M-S"); `unbound` is the list of disabled
   * command IDs. A consuming app (Hub) stores this verbatim and hands it back
   * through loadOverrides() on the next mount.
   */
  serializeOverrides() {
    const overrides = {};
    for (const [id, seq] of this.overrideStorage) overrides[id] = sequenceKey(seq);
    return { overrides, unbound: [...this.unbound].sort() };
  }
  /**
   * Load override state produced by serializeOverrides() (or any consumer with
   * the same shape). Replaces the current override state and rebuilds the
   * effective bindings.
   */
  loadOverrides(data) {
    this.overrideStorage.clear();
    this.unbound.clear();
    if (data.overrides) {
      for (const [id, seqStr] of Object.entries(data.overrides)) {
        this.overrideStorage.set(id, parseSequence(seqStr));
      }
    }
    if (data.unbound) {
      for (const id of data.unbound) this.unbound.add(id);
    }
    this.rebuildEffective();
  }
  /**
   * Override-induced collisions: a chord where a user override (or a second
   * default) landed on top of another command's effective chord. Non-empty
   * means a UI should warn — the displaced command lost that chord. Prefix
   * collisions involving an override are also reported for every known mode:
   * an exact shorter command would prevent typing the longer command.
   */
  overrideConflicts() {
    return [...this.overrideCollisions, ...this.prefixOverrideConflicts()];
  }
  prefixOverrideConflicts() {
    const modes = new Set([...this.defaults.keys()].filter((scope) => scope !== "global"));
    for (const command of this.registry.list()) {
      for (const mode of command.modes ?? []) modes.add(mode);
    }
    const conflicts = [];
    const reported = /* @__PURE__ */ new Set();
    for (const mode of [null, ...[...modes].sort()]) {
      const scopes = mode === null ? ["global"] : [mode, "global"];
      const seen = /* @__PURE__ */ new Set();
      const effective = [];
      for (const scope of scopes) {
        for (const binding of this.bindings.get(scope) ?? []) {
          const key = sequenceKey(binding.sequence);
          if (seen.has(key)) continue;
          seen.add(key);
          const definition = this.registry.get(binding.commandId)?.def;
          if (!definition || definition.modes && (mode === null || !definition.modes.has(mode))) continue;
          effective.push({ binding, key });
        }
      }
      for (let i = 0; i < effective.length; i++) {
        for (let j = i + 1; j < effective.length; j++) {
          const left = effective[i];
          const right = effective[j];
          if (left.binding.commandId === right.binding.commandId) continue;
          const shorter = left.key.startsWith(right.key + " ") ? right : left;
          const longer = shorter === left ? right : left;
          if (!longer.key.startsWith(shorter.key + " ")) continue;
          for (const overridden of [shorter, longer]) {
            if (!this.overrideStorage.has(overridden.binding.commandId)) continue;
            const other = overridden === shorter ? longer : shorter;
            const conflict = {
              sequenceKey: shorter.key,
              scope: mode ?? "global",
              existingCommandId: other.binding.commandId,
              newCommandId: overridden.binding.commandId
            };
            const identity = JSON.stringify(conflict);
            if (!reported.has(identity)) {
              reported.add(identity);
              conflicts.push(conflict);
            }
          }
        }
      }
    }
    return conflicts;
  }
  /**
   * Rebuild the EFFECTIVE binding state (this.bindings / this.index) from the
   * source of truth: factory defaults + user overrides − disabled commands.
   *   Pass 1 places every NON-overridden default at its factory chord.
   *   Pass 2 places every OVERRIDDEN command at its override chord; it WINS
   *   the chord, displacing whatever pass 1 placed there, and records the
   *   displacement as an override collision so the UI can surface it.
   * A command bound in several scopes gets its override applied in each; the
   * inInput flag of the original binding is carried through. resolve(),
   * findBindingByChord(), help() and isPendingViable() read the effective
   * state, so one rebuild is what makes an override take runtime effect
   * everywhere at once.
   */
  rebuildEffective() {
    this.bindings.clear();
    this.index.clear();
    for (const scope of this.defaults.keys()) {
      this.bindings.set(scope, []);
      this.index.set(scope, /* @__PURE__ */ new Map());
    }
    this.overrideCollisions = [];
    for (const pass of [1, 2]) {
      for (const [scope, list] of this.defaults) {
        const effIndex = this.index.get(scope);
        const effList = this.bindings.get(scope);
        for (const b of list) {
          const overridden = this.overrideStorage.has(b.commandId);
          if (pass === 1 ? overridden : !overridden) continue;
          if (this.unbound.has(b.commandId)) continue;
          const seq = this.overrideStorage.get(b.commandId) ?? b.sequence;
          const key = sequenceKey(seq);
          const occupant = effIndex.get(key);
          if (occupant === b.commandId) continue;
          if (occupant !== void 0) {
            this.overrideCollisions.push({
              sequenceKey: key,
              scope,
              existingCommandId: occupant,
              newCommandId: b.commandId
            });
            if (pass === 1) continue;
            const displaced = effList.findIndex((bound) => sequenceKey(bound.sequence) === key);
            effList.splice(displaced, 1);
          }
          effIndex.set(key, b.commandId);
          effList.push({ sequence: seq, commandId: b.commandId, inInput: b.inInput });
        }
      }
    }
  }
  /**
   * Resolve a completed chord sequence to a command ID, walking scope priority:
   * the active mode first, then global. Returns null when nothing is bound.
   */
  resolve(sequence) {
    const key = sequenceKey(sequence);
    const scopes = this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const id = this.index.get(scope)?.get(key);
      if (id !== void 0) return { commandId: id, scope };
    }
    return null;
  }
  /** Whether the in-progress `pending` sequence is a prefix of any binding in
   *  the effective scope chain — keeps a multi-chord command alive while the
   *  user types it, and expires it the moment no binding could complete. */
  isPendingViable() {
    const key = sequenceKey(this.pending);
    const scopes = this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const scopeIndex = this.index.get(scope);
      if (!scopeIndex) continue;
      for (const bound of scopeIndex.keys()) {
        if (bound === key || bound.startsWith(key + " ")) return true;
      }
    }
    return false;
  }
  inInputElement(target) {
    if (!(target instanceof HTMLElement)) return false;
    return target.closest(INPUT_SELECTOR) !== null;
  }
  findBindingByChord(sequence) {
    const key = sequenceKey(sequence);
    const scopes = this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      const binding = list.find((b) => sequenceKey(b.sequence) === key);
      if (binding) return { binding, scope };
    }
    return null;
  }
  handleKeydown(event) {
    const ev = event;
    const key = ev.key;
    if (this.composing || ev.isComposing || ev.keyCode === 229 || ev.which === 229 || key === "Dead" || key === "Process" || key === "AltGraph" || ev.defaultPrevented || typeof ev.getModifierState === "function" && ev.getModifierState("AltGraph")) {
      this.resetPending();
      return;
    }
    const ctrlKey = ev.ctrlKey;
    const altKey = ev.altKey;
    const shiftKey = ev.shiftKey;
    const metaKey = ev.metaKey;
    if (typeof key !== "string") return;
    const preventDefault = () => ev.preventDefault();
    const target = ev.target ?? null;
    const chord = eventToChord({ key, ctrlKey, altKey, shiftKey, metaKey });
    if (chord === null) return;
    if (this.inInputElement(target)) {
      const probe = this.findBindingByChord([...this.pending, chord]);
      if (!probe || !probe.binding.inInput) {
        this.resetPending();
        return;
      }
    }
    this.pending = [...this.pending, chord];
    const hit = this.findBindingByChord(this.pending);
    if (hit && sequenceKey(hit.binding.sequence) === sequenceKey(this.pending)) {
      const consumed = this.registry.run(hit.binding.commandId, { via: "keyboard", source: target }, void 0);
      if (consumed) preventDefault();
      this.resetPending();
      return;
    }
    if (this.isPendingViable()) {
      preventDefault();
      return;
    }
    this.resetPending();
  }
  /** Programmatic dispatch of a full sequence (agent / button path converges
   *  here too). Returns the command ID run, or null. */
  dispatchSequence(sequenceStr, via = "program") {
    const seq = parseSequence(sequenceStr);
    const hit = this.resolve(seq);
    if (!hit) return null;
    const ok = this.registry.run(hit.commandId, { via });
    return ok ? hit.commandId : null;
  }
  resetPending() {
    this.pending = [];
  }
  /** Attach the keydown listener. Returns a detach function — the lifecycle
   *  cleanup for SPA navigation. Callers (the shell or an app) hold the
   *  returned function and call it on teardown. */
  attach(target = document) {
    target.addEventListener("keydown", this.onKeydown, true);
    target.addEventListener("compositionstart", this.onCompositionStart, true);
    target.addEventListener("compositionend", this.onCompositionEnd, true);
    return () => {
      target.removeEventListener("keydown", this.onKeydown, true);
      target.removeEventListener("compositionstart", this.onCompositionStart, true);
      target.removeEventListener("compositionend", this.onCompositionEnd, true);
      this.composing = false;
      this.resetPending();
    };
  }
  /** The introspection model: current mode + every command with the chords
   *  bound to it (resolved across scopes). Feeds the help UI and agent tools.
   *  Reports the EFFECTIVE chords (overrides applied, unbinds honored,
   *  mode-shadowed chords omitted). */
  help() {
    const byCommand = /* @__PURE__ */ new Map();
    const seen = /* @__PURE__ */ new Set();
    const scopes = this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      for (const b of list) {
        const key = sequenceKey(b.sequence);
        if (seen.has(key)) continue;
        seen.add(key);
        const arr = byCommand.get(b.commandId) ?? [];
        arr.push(key);
        byCommand.set(b.commandId, arr);
      }
    }
    return {
      mode: this.currentMode,
      commands: this.registry.list().map((c) => ({
        ...c,
        chords: byCommand.get(c.id) ?? []
      }))
    };
  }
};

// ts/shell/workspace-commands/_WorkspaceCommands.ts
var owners = /* @__PURE__ */ new WeakMap();
var nextId = 0;
function composing(event) {
  return event.isComposing || event.keyCode === 229 || ["Dead", "Process", "Unidentified"].includes(event.key) || event.getModifierState("AltGraph");
}
var WorkspaceCommands = class extends BaseComponent {
  keymap;
  ids;
  trigger;
  panel;
  search;
  results;
  status;
  detach;
  destroyed = false;
  compositionActive = false;
  visibleIds = [];
  constructor(config) {
    super(config);
    if (config.keymap.commands !== config.registry) {
      throw new Error("WorkspaceCommands requires the keymap's command registry");
    }
    if (owners.has(config.keymap)) throw new Error("WorkspaceCommands already owns this keymap");
    this.keymap = config.keymap;
    this.ids = [...new Set(config.commandIds)];
    this.container.classList.add("stx-workspace-commands");
    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.textContent = gettext("Commands");
    this.trigger.setAttribute("aria-expanded", "false");
    this.panel = document.createElement("section");
    this.panel.id = `stx-workspace-commands-${++nextId}`;
    this.panel.className = "stx-workspace-commands__panel";
    this.panel.setAttribute("aria-label", gettext("Workspace commands"));
    this.panel.hidden = true;
    this.panel.addEventListener("compositionstart", () => {
      this.compositionActive = true;
    });
    this.panel.addEventListener("compositionend", () => {
      this.compositionActive = false;
    });
    this.trigger.setAttribute("aria-controls", this.panel.id);
    this.search = document.createElement("input");
    this.search.type = "search";
    this.search.setAttribute("aria-label", gettext("Find command"));
    this.search.placeholder = gettext("Find command");
    this.search.addEventListener("input", () => this.refresh());
    this.search.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || this.compositionActive || composing(event)) return;
      if (event.key === "Enter" && this.visibleIds.length) {
        if (this.run(this.visibleIds[0], "keyboard")) event.preventDefault();
      }
    });
    this.panel.addEventListener("keydown", (event) => {
      if (event.defaultPrevented || this.compositionActive || composing(event)) return;
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        this.close();
        this.trigger.focus();
      }
    });
    this.trigger.addEventListener("click", () => this.panel.hidden ? this.open() : this.close());
    this.results = document.createElement("div");
    this.status = document.createElement("p");
    this.status.setAttribute("role", "status");
    this.panel.append(this.search, this.results, this.status);
    this.container.append(this.trigger, this.panel);
    this.detach = this.keymap.attach(config.keyboardTarget ?? document);
    owners.set(this.keymap, this);
    this.refresh();
  }
  open() {
    if (this.destroyed) return;
    this.panel.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
    this.search.value = "";
    this.status.textContent = "";
    this.refresh();
    this.search.focus();
  }
  close() {
    this.panel.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
  }
  /** Refresh after the host changes commands, modes, or loaded preferences. */
  refresh() {
    if (this.destroyed) return;
    const focusedRow = document.activeElement?.closest(".stx-workspace-commands__row");
    const restoreFocus = focusedRow && this.results.contains(focusedRow) ? focusedRow.dataset.commandId : void 0;
    this.results.replaceChildren();
    const query = this.search.value.trim().toLocaleLowerCase();
    const commands = this.config.registry.list().filter((command) => command.active && this.ids.includes(command.id) && command.label.toLocaleLowerCase().includes(query));
    this.visibleIds = commands.map((command) => command.id);
    const help = this.keymap.help().commands;
    for (const command of commands) {
      const row = document.createElement("div");
      row.className = "stx-workspace-commands__row";
      row.dataset.commandId = command.id;
      const run = this.button(command.label, () => this.run(command.id, "button"));
      run.dataset.commandId = command.id;
      const shortcut = document.createElement("input");
      shortcut.type = "text";
      shortcut.setAttribute("aria-label", `${gettext("Shortcut for")} ${command.label}`);
      shortcut.placeholder = "C-x C-p";
      shortcut.value = help.find((entry) => entry.id === command.id)?.chords[0] ?? "";
      const apply = this.button(gettext("Apply shortcut"), () => this.apply(command.id, shortcut.value));
      const disable = this.button(gettext("Disable shortcut"), () => {
        this.keymap.unbind(command.id);
        this.changed();
      });
      const reset = this.button(gettext("Reset shortcut"), () => {
        this.editShortcut(command.id, () => {
          const preferences = this.keymap.serializeOverrides();
          delete preferences.overrides[command.id];
          preferences.unbound = preferences.unbound.filter((id) => id !== command.id);
          this.keymap.loadOverrides(preferences);
        });
      });
      const hasFactoryBinding = this.keymap.hasFactoryBinding(command.id);
      apply.disabled = disable.disabled = reset.disabled = !hasFactoryBinding;
      row.append(run, shortcut, apply, disable, reset);
      this.results.append(row);
      if (restoreFocus === command.id) shortcut.focus();
    }
    if (!commands.length) {
      const empty = document.createElement("p");
      empty.textContent = gettext("No matching commands");
      this.results.append(empty);
    }
    const hint = document.createElement("p");
    hint.textContent = gettext("Shortcut notation: C = Ctrl, M = Alt, S = Shift, M2 = Command. Separate keys with spaces.");
    this.results.append(hint);
  }
  button(label, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      if (!this.destroyed) action();
    });
    return button;
  }
  run(id, via) {
    if (this.destroyed || !this.ids.includes(id) || !this.config.registry.get(id)?.active) return false;
    this.close();
    this.trigger.focus();
    return this.config.registry.run(id, { via, source: this.search });
  }
  apply(id, sequence) {
    this.editShortcut(id, () => {
      if (!parseSequence(sequence).length) throw new Error(gettext("Enter a shortcut"));
      this.keymap.enable(id);
      this.keymap.setOverride(id, sequence);
    });
  }
  editShortcut(id, edit) {
    const previous = this.keymap.serializeOverrides();
    try {
      edit();
      const conflict = this.keymap.overrideConflicts().find((item) => item.newCommandId === id || item.existingCommandId === id);
      if (conflict) throw new Error(`${gettext("Shortcut already used by")} ${conflict.existingCommandId === id ? conflict.newCommandId : conflict.existingCommandId}`);
    } catch (error) {
      this.keymap.loadOverrides(previous);
      this.status.textContent = error instanceof Error ? error.message : gettext("Invalid shortcut");
      return;
    }
    this.changed();
  }
  changed() {
    this.status.textContent = gettext("Shortcut updated");
    this.refresh();
    this.config.onPreferencesChange?.(this.keymap.serializeOverrides());
  }
  destroy() {
    if (this.destroyed) return;
    this.destroyed = true;
    this.compositionActive = false;
    this.detach();
    if (owners.get(this.keymap) === this) owners.delete(this.keymap);
    super.destroy();
  }
};
export {
  CommandRegistry,
  Keymap,
  WorkspaceCommands
};
