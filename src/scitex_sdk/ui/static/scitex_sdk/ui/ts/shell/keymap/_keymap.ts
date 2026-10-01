/**
 * The Keymap — Emacs major-mode semantics over the Command Registry.
 *
 * A GLOBAL keymap is always active. An active page/app MODE adds a mode keymap
 * on top: bindings are resolved mode-first, so a mode can shadow a global
 * chord (e.g. an editor mode rebinding C-c) without touching the global map.
 * Activating a mode is what makes mode-scoped commands in the registry active.
 *
 * KEYBOARD-FIRST, NOT MOUSE-ONLY. Every command reaches the same action a
 * button would, through `Keymap.dispatchSequence` — the keyboard IS the
 * primary interface, the button is an alternative caller of the same command.
 *
 * INPUT/CONTENTEDITABLE SUPPRESSION. A keydown inside a text field, textarea,
 * select, or [contenteditable] does NOT fire command chords UNLESS the binding
 * opted in (a binding's `inInput: true`). This is the default that keeps C-c
 * from eating a copy in an editor; an app opts a specific binding in when it
 * genuinely wants it there (e.g. a terminal that captures everything).
 *
 * CONFLICT DETECTION is at bind time, not keypress time: binding the same
 * chord to two commands in the same scope is reported immediately so the
 * authoring app sees it, rather than the user hitting a silent one-wins.
 *
 * USER OVERRIDES ARE REAL STATE, NOT A DEAD WRITE. A user rebind (setOverride)
 * and a disable (unbind) live in an overlay on top of the factory defaults,
 * and every mutation REBUILDS the effective binding state from that overlay.
 * resolve()/findBindingByChord()/help()/dispatchSequence() all read the
 * EFFECTIVE state, so an override actually changes keyboard + program dispatch
 * and the help UI. (In 0.22.0 setOverride wrote overrideStorage but nothing
 * ever read it — a persisted user shortcut had no runtime effect. That is the
 * write-only defect this fix removes.) The overlay is pure-JSON-serializable
 * (serializeOverrides/loadOverrides) so a consuming app (Hub) can persist it.
 */

import {
  type Chord,
  type Sequence,
  parseChord,
  parseSequence,
  sequenceKey,
  eventToChord,
  chordMatches,
} from "./_chords";
import { CommandRegistry, globalRegistry } from "./_registry";

/** A single chord-to-command binding. */
export interface Binding {
  /** The sequence, e.g. "C-x C-s" or "C-c". Stored canonical. */
  sequence: Sequence;
  /** The command ID to run when the sequence completes. */
  commandId: string;
  /** When true, the binding fires even inside input/contenteditable. */
  inInput?: boolean;
}

export type BindingScope = "global" | string; // string = a mode name

export interface Conflict {
  sequenceKey: string;
  scope: BindingScope;
  existingCommandId: string;
  newCommandId: string;
}

export interface KeymapOptions {
  registry?: CommandRegistry;
  /** Initial user-override overlay (commandId -> sequence). Defaults to empty;
   *  a consuming app typically seeds it from persisted override data, or
   *  loads it after bind() setup via loadOverrides(). */
  overrideStorage?: Map<string, Sequence>;
}

const INPUT_SELECTOR =
  "input, textarea, select, [contenteditable=''], [contenteditable='true'], [contenteditable='plaintext-only']";

export class Keymap {
  private readonly registry: CommandRegistry;

  /** SOURCE OF TRUTH: the factory bindings the app adds via bind(), per scope.
   *  User overrides never mutate this — they are an overlay (overrideStorage /
   *  unbound) applied on top during rebuildEffective(). "global" is always
   *  present. */
  private readonly defaults = new Map<BindingScope, Binding[]>();

  /** The user override overlay: commandId -> the chord it now runs on. */
  private readonly overrideStorage: Map<string, Sequence>;

  /** Command IDs the user has disabled. A disabled command keeps its factory
   *  default (so enable()/resetOverrides() restore exactly what was there) but
   *  contributes no effective chord while disabled. */
  private readonly unbound = new Set<string>();

  /** Override-induced collisions (an override landed on another command's
   *  effective chord). Surfaced via overrideConflicts() — never silent. */
  private overrideCollisions: Conflict[] = [];

  /** EFFECTIVE state (defaults + overrides − unbound): scope -> bindings.
   *  resolve/findBindingByChord/help read THIS, and it is rebuilt by
   *  rebuildEffective() after every mutation. */
  private readonly bindings = new Map<BindingScope, Binding[]>();
  /** EFFECTIVE state: scope -> canonical-sequence-key -> commandId (O(1) + conflicts). */
  private readonly index = new Map<BindingScope, Map<string, string>>();

  /** Pending prefix sequence while a multi-chord command is being typed. */
  private pending: Sequence = [];
  // Typed as Event (not KeyboardEvent) so it satisfies addEventListener's
  // EventListener signature; handleKeydown duck-types the keyboard fields.
  private readonly onKeydown: (event: Event) => void;

  constructor(options: KeymapOptions = {}) {
    this.registry = options.registry ?? globalRegistry;
    this.overrideStorage = options.overrideStorage ?? new Map();
    this.defaults.set("global", []);
    this.onKeydown = (event) => this.handleKeydown(event);
    this.rebuildEffective();
  }

  get currentMode(): string | null {
    return this.registry.currentMode;
  }

  /** Activate a page/app mode. Installs the scope so it is bindable, and
   *  tells the registry which mode-scoped commands are now live. */
  activateMode(mode: string): void {
    this.ensureScope(mode);
    this.registry.setMode(mode);
    this.resetPending();
  }

  /** Return to global-only. Mode-scoped commands go inactive. */
  deactivateMode(): void {
    this.registry.setMode(null);
    this.resetPending();
  }

  /** Ensure a (non-global) scope exists in the defaults table so it is bindable. */
  private ensureScope(scope: BindingScope): void {
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
  bind(scope: BindingScope, sequenceStr: string, commandId: string, inInput = false): Conflict | null {
    this.ensureScope(scope);
    const seq = parseSequence(sequenceStr);
    const key = sequenceKey(seq);
    const existing = this.index.get(scope)?.get(key);
    if (existing !== undefined && existing !== commandId) {
      return { sequenceKey: key, scope, existingCommandId: existing, newCommandId: commandId };
    }
    if (existing === commandId) return null; // idempotent re-bind
    this.defaults.get(scope)!.push({ sequence: seq, commandId, inInput });
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
  setOverride(commandId: string, sequenceStr: string): void {
    this.overrideStorage.set(commandId, parseSequence(sequenceStr));
    this.rebuildEffective();
  }

  /**
   * Disable a command: it contributes no effective chord while disabled, but
   * its factory default is PRESERVED (so enable()/resetOverrides() restore
   * exactly what was there, not a rebuilt guess). Any override on it is
   * dropped — a disabled command has no chord to override.
   */
  unbind(commandId: string): void {
    this.unbound.add(commandId);
    this.overrideStorage.delete(commandId);
    this.rebuildEffective();
  }

  /** Re-enable a previously disabled command at its factory default chord. */
  enable(commandId: string): void {
    this.unbound.delete(commandId);
    this.rebuildEffective();
  }

  /** Reset every user override AND every unbind; factory defaults restored. */
  resetOverrides(): void {
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
  serializeOverrides(): { overrides: Record<string, string>; unbound: string[] } {
    const overrides: Record<string, string> = {};
    for (const [id, seq] of this.overrideStorage) overrides[id] = sequenceKey(seq);
    return { overrides, unbound: [...this.unbound].sort() };
  }

  /**
   * Load override state produced by serializeOverrides() (or any consumer with
   * the same shape). Replaces the current override state and rebuilds the
   * effective bindings.
   */
  loadOverrides(data: { overrides?: Record<string, string>; unbound?: string[] }): void {
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
   * means a UI should warn — the displaced command lost that chord. This is
   * the "no silent one-wins" guarantee for the override path.
   */
  overrideConflicts(): Conflict[] {
    return [...this.overrideCollisions];
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
  private rebuildEffective(): void {
    this.bindings.clear();
    this.index.clear();
    for (const scope of this.defaults.keys()) {
      this.bindings.set(scope, []);
      this.index.set(scope, new Map());
    }
    this.overrideCollisions = [];
    for (const pass of [1, 2]) {
      for (const [scope, list] of this.defaults) {
        const effIndex = this.index.get(scope)!;
        const effList = this.bindings.get(scope)!;
        for (const b of list) {
          const overridden = this.overrideStorage.has(b.commandId);
          if (pass === 1 ? overridden : !overridden) continue; // each pass owns its half
          if (this.unbound.has(b.commandId)) continue; // disabled contributes no chord
          const seq = this.overrideStorage.get(b.commandId) ?? b.sequence;
          const key = sequenceKey(seq);
          const occupant = effIndex.get(key);
          if (occupant === b.commandId) continue; // idempotent (same command already here)
          if (occupant !== undefined) {
            this.overrideCollisions.push({
              sequenceKey: key,
              scope,
              existingCommandId: occupant,
              newCommandId: b.commandId,
            });
            if (pass === 1) continue; // two defaults colliding: first wins (bind() prevents this)
            // pass 2: the user's override wins the chord it displaced onto.
            effIndex.set(key, b.commandId);
            effList.push({ sequence: seq, commandId: b.commandId, inInput: b.inInput });
            continue;
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
  resolve(sequence: Sequence): { commandId: string; scope: BindingScope } | null {
    const key = sequenceKey(sequence);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const id = this.index.get(scope)?.get(key);
      if (id !== undefined) return { commandId: id, scope };
    }
    return null;
  }

  /** Whether the in-progress `pending` sequence is a prefix of any binding in
   *  the effective scope chain — keeps a multi-chord command alive while the
   *  user types it, and expires it the moment no binding could complete. */
  private isPendingViable(): boolean {
    const key = sequenceKey(this.pending);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const scopeIndex = this.index.get(scope);
      if (!scopeIndex) continue;
      for (const bound of scopeIndex.keys()) {
        if (bound === key || bound.startsWith(key + " ")) return true;
      }
    }
    return false;
  }

  private inInputElement(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    return target.closest(INPUT_SELECTOR) !== null;
  }

  private findBindingByChord(sequence: Sequence): { binding: Binding; scope: BindingScope } | null {
    const key = sequenceKey(sequence);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      const binding = list.find((b) => sequenceKey(b.sequence) === key);
      if (binding) return { binding, scope };
    }
    return null;
  }

  private handleKeydown(event: Event): void {
    // `as KeyboardEvent` is a type assertion (no runtime cost). The fields are
    // present on any real keydown event; harnesses (vitest/jsdom) that pass
    // plain objects still satisfy the read.
    const ev = event as KeyboardEvent;
    const key = ev.key;
    const ctrlKey = ev.ctrlKey;
    const altKey = ev.altKey;
    const shiftKey = ev.shiftKey;
    const metaKey = ev.metaKey;
    if (typeof key !== "string") return;
    const preventDefault = () => ev.preventDefault();
    const target = ev.target ?? null;
    const chord: Chord | null = eventToChord({ key, ctrlKey, altKey, shiftKey, metaKey });
    if (chord === null) return;

    // Suppression: inside an input, only bindings that opted in fire. A bare
    // modifier or a non-optimised chord inside input is passed through.
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
      // Exact match: dispatch the command. Conditional consumption — swallow
      // the key ONLY when the command actually consumed it (ran AND its action
      // didn't report a no-op). A no-op (e.g. "delete" with nothing selected)
      // returns false, so we do NOT preventDefault and the key's native
      // browser behavior is preserved. See CommandDef.action.
      const consumed = this.registry.run(hit.binding.commandId, { via: "keyboard", source: target }, undefined);
      if (consumed) preventDefault();
      this.resetPending();
      return;
    }

    if (this.isPendingViable()) {
      // A real prefix — swallow the key so it doesn't also type into the page.
      preventDefault();
      return;
    }

    // Dead end: no binding can complete from here. Expire and let the key do
    // whatever the page would have done with it.
    this.resetPending();
  }

  /** Programmatic dispatch of a full sequence (agent / button path converges
   *  here too). Returns the command ID run, or null. */
  dispatchSequence(sequenceStr: string, via: "button" | "agent" | "program" = "program"): string | null {
    const seq = parseSequence(sequenceStr);
    const hit = this.resolve(seq);
    if (!hit) return null;
    const ok = this.registry.run(hit.commandId, { via });
    return ok ? hit.commandId : null;
  }

  private resetPending(): void {
    this.pending = [];
  }

  /** Attach the keydown listener. Returns a detach function — the lifecycle
   *  cleanup for SPA navigation. Callers (the shell or an app) hold the
   *  returned function and call it on teardown. */
  attach(target: EventTarget = document): () => void {
    target.addEventListener("keydown", this.onKeydown, true);
    return () => target.removeEventListener("keydown", this.onKeydown, true);
  }

  /** The introspection model: current mode + every command with the chords
   *  bound to it (resolved across scopes). Feeds the help UI and agent tools.
   *  Reports the EFFECTIVE chords (overrides applied, unbinds honored). */
  help(): {
    mode: string | null;
    commands: Array<{
      id: string;
      label: string;
      group?: string;
      active: boolean;
      chords: string[];
    }>;
  } {
    // map commandId -> chord display strings, mode-first
    const byCommand = new Map<string, string[]>();
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes.reverse()) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      for (const b of list) {
        const arr = byCommand.get(b.commandId) ?? [];
        arr.push(sequenceKey(b.sequence));
        byCommand.set(b.commandId, arr);
      }
    }
    return {
      mode: this.currentMode,
      commands: this.registry.list().map((c) => ({
        ...c,
        chords: byCommand.get(c.id) ?? [],
      })),
    };
  }
}

export { parseChord, chordMatches };
