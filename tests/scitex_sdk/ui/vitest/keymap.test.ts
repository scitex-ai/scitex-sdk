/**
 * Keymap primitive: chord parsing, registry dispatch, runtime behaviour
 * (mode shadowing, input suppression, prefix expiry, lifecycle), and the
 * help() introspection model. `npx vitest run`
 *
 * Most tests drive Keymap.handleKeydown with plain keyboard-field objects.
 * Collision regressions also dispatch real, cancelable KeyboardEvents through
 * attach() on isolated elements, so prior document listeners cannot interfere.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommandRegistry,
  Keymap,
  parseChord,
  parseSequence,
  sequenceKey,
  chordToString,
  eventToChord,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/shell/keymap";

/* ── Chord grammar ─────────────────────────────────────────────────────── */

describe("chord parsing", () => {
  it("parses a bare letter key case-insensitively", () => {
    expect(parseChord("x").key).toBe("x");
    expect(parseChord("X").key).toBe("x");
  });

  it("parses the Emacs modifier tokens C/M/S/M2 into flags", () => {
    expect(parseChord("C-x")).toEqual({ ctrl: true, alt: false, shift: false, meta: false, key: "x" });
    expect(parseChord("M-g")).toEqual({ ctrl: false, alt: true, shift: false, meta: false, key: "g" });
    expect(parseChord("S-A")).toEqual({ ctrl: false, alt: false, shift: true, meta: false, key: "a" });
    expect(parseChord("M2-C-RET")).toEqual({ ctrl: true, alt: false, shift: false, meta: true, key: "return" });
  });

  it("maps named keys to their canonical single-token form", () => {
    expect(parseChord("RET").key).toBe("return");
    expect(parseChord("SPAC").key).toBe(" ");
    expect(parseChord("ESC").key).toBe("escape");
    expect(parseChord("F1").key).toBe("F1");
    expect(parseChord("UP").key).toBe("up");
  });

  it("parses a prefix-command sequence into multiple chords", () => {
    const seq = parseSequence("C-x C-s");
    expect(seq).toHaveLength(2);
    expect(seq[0]).toMatchObject({ ctrl: true, key: "x" });
    expect(seq[1]).toMatchObject({ ctrl: true, key: "s" });
  });

  it("round-trips a chord through sequenceKey deterministically", () => {
    expect(sequenceKey(parseSequence("C-x C-s"))).toBe("C-X C-S");
    expect(chordToString(parseChord("M-g"))).toBe("M-G");
  });

  it("eventToChord ignores bare modifier presses (no command intent)", () => {
    expect(eventToChord({ key: "Shift", ctrlKey: false, altKey: false, shiftKey: true, metaKey: false })).toBeNull();
    expect(eventToChord({ key: "Control", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false })).toBeNull();
  });

  it("eventToChord canonicalizes a real Ctrl+X keydown the same as parseChord('C-x')", () => {
    const fromEvent = eventToChord({ key: "x", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false });
    expect(fromEvent).toEqual(parseChord("C-x"));
  });
});

/* ── Registry: one command function, stable IDs, mode activeness ───────── */

describe("CommandRegistry", () => {
  it("runs a registered command through the single dispatch path", () => {
    const reg = new CommandRegistry();
    const calls: Array<unknown> = [];
    reg.set({ id: "save", label: "Save", action: (p) => calls.push(p) });
    expect(reg.run("save", { via: "keyboard" }, "payload")).toBe(true);
    expect(calls).toEqual(["payload"]);
  });

  it("returns false for an unknown command id", () => {
    const reg = new CommandRegistry();
    expect(reg.run("missing")).toBe(false);
  });

  it("keeps a mode-scoped command inactive until its mode is active", () => {
    const reg = new CommandRegistry();
    const ran: string[] = [];
    reg.set({ id: "editor:undo", label: "Undo", modes: new Set(["editor"]), action: () => ran.push("undo") });
    reg.run("editor:undo");
    expect(ran).toEqual([]);
    reg.setMode("editor");
    reg.run("editor:undo");
    expect(ran).toEqual(["undo"]);
  });

  it("lists commands with stable sorted ids and their active flag", () => {
    const reg = new CommandRegistry();
    reg.set({ id: "b", label: "B", action: () => {} });
    reg.set({ id: "a", label: "A", action: () => {} });
    reg.set({ id: "c", label: "C", modes: new Set(["m"]), action: () => {} });
    reg.setMode("m");
    expect(reg.ids()).toEqual(["a", "b", "c"]);
    const list = reg.list();
    expect(list.find((x) => x.id === "c")!.active).toBe(true);
    reg.setMode(null);
    expect(reg.list().find((x) => x.id === "c")!.active).toBe(false);
  });
});

/* ── Keymap runtime ────────────────────────────────────────────────────── */

function key(opts: { key: string; ctrl?: boolean; alt?: boolean; shift?: boolean; meta?: boolean; target?: EventTarget | null }): any {
  const prevented = { called: false };
  return {
    key: opts.key,
    ctrlKey: !!opts.ctrl,
    altKey: !!opts.alt,
    shiftKey: !!opts.shift,
    metaKey: !!opts.meta,
    target: opts.target ?? null,
    preventDefault: () => { prevented.called = true; },
    _prevented: prevented,
  };
}

function dispatchKey(
  map: Keymap,
  init: KeyboardEventInit,
  target: HTMLElement = document.createElement("div"),
): KeyboardEvent {
  const detach = map.attach(target);
  const event = new KeyboardEvent("keydown", { ...init, bubbles: true, cancelable: true });
  try {
    target.dispatchEvent(event);
  } finally {
    detach();
  }
  return event;
}

describe("Keymap runtime", () => {
  let reg: CommandRegistry;
  let map: Keymap;
  let detachFn: (() => void) | undefined;

  beforeEach(() => {
    document.body.innerHTML = "";
    reg = new CommandRegistry();
    map = new Keymap({ registry: reg });
    detachFn = map.attach(document);
  });

  it("fires a global binding on a full chord and swallows the key", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    const ev = key({ key: "s", ctrl: true });
    map["handleKeydown"](ev as any);
    expect(reg.get("save")!.active).toBe(true);
    expect(ev._prevented.called).toBe(true);
  });

  it("detects a chord conflict when binding the same chord to a different command", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    const conflict = map.bind("global", "C-s", "close");
    expect(conflict).not.toBeNull();
    expect(conflict!.existingCommandId).toBe("save");
    expect(conflict!.newCommandId).toBe("close");
    // the original binding is not clobbered silently
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("save");
  });

  it("resolves a mode binding in preference to a global one (shadowing)", () => {
    reg.set({ id: "global-s", label: "G", action: vi.fn() });
    reg.set({ id: "editor-s", label: "E", action: vi.fn() });
    expect(map.bind("global", "C-s", "global-s")).toBeNull();
    expect(map.bind("editor", "C-s", "editor-s")).toBeNull();
    map.activateMode("editor");
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("editor-s");
    map.deactivateMode();
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("global-s");
  });

  it("tracks a multi-chord prefix and fires only when it completes", () => {
    const run = vi.fn();
    reg.set({ id: "save-buffer", label: "Save buffer", action: run });
    expect(map.bind("global", "C-x C-s", "save-buffer")).toBeNull();
    // first chord is a live prefix: swallowed, not fired
    map["handleKeydown"](key({ key: "x", ctrl: true }) as any);
    expect(run).not.toHaveBeenCalled();
    // completing chord fires
    map["handleKeydown"](key({ key: "s", ctrl: true }) as any);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("expires a dead-end prefix and lets the next key be fresh", () => {
    const run = vi.fn();
    reg.set({ id: "solo", label: "Solo", action: run });
    expect(map.bind("global", "C-s", "solo")).toBeNull();
    // 'c' is not the start of any bound sequence -> pending stays empty
    map["handleKeydown"](key({ key: "c" }) as any);
    // then a bare C-s still fires
    map["handleKeydown"](key({ key: "s", ctrl: true }) as any);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("suppresses chords inside an input unless the binding opted in", () => {
    const run = vi.fn();
    reg.set({ id: "copy", label: "Copy", action: run });
    expect(map.bind("global", "C-c", "copy")).toBeNull(); // NOT inInput
    const input = document.createElement("input");
    document.body.appendChild(input);
    map["handleKeydown"](key({ key: "c", ctrl: true, target: input }) as any);
    expect(run).not.toHaveBeenCalled(); // suppressed in the field

    reg.set({ id: "term", label: "Term", action: run });
    expect(map.bind("global", "C-c", "term", true)).not.toBeNull(); // conflict: C-c already bound
    // unbind the non-input one so the inInput one can occupy the chord
    map.unbind("copy");
    expect(map.bind("global", "C-c", "term", true)).toBeNull();
    map["handleKeydown"](key({ key: "c", ctrl: true, target: input }) as any);
    expect(run).toHaveBeenCalledTimes(1); // fires because inInput
  });

  it("converges button/agent/program dispatch on the same command", () => {
    const run = vi.fn();
    reg.set({ id: "run", label: "Run", action: run });
    expect(map.bind("global", "C-r", "run")).toBeNull();
    expect(map.dispatchSequence("C-r", "agent")).toBe("run");
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("attach() returns a detach that removes the keydown listener (lifecycle cleanup)", () => {
    const removeSpy = vi.spyOn(document, "removeEventListener");
    expect(document.removeEventListener).not.toHaveBeenCalled();
    // The detach returned by attach() must remove exactly the keydown listener.
    detachFn!();
    expect(removeSpy).toHaveBeenCalledWith("keydown", map["onKeydown"], true);
    removeSpy.mockRestore();
  });

  it("help() reports the active mode and the chords bound to each command", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "ed:undo", label: "Undo", action: vi.fn(), modes: new Set(["editor"]) });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("editor", "M-/", "ed:undo")).toBeNull();
    map.activateMode("editor");
    const help = map.help();
    expect(help.mode).toBe("editor");
    const save = help.commands.find((c) => c.id === "save")!;
    expect(save.chords).toContain("C-S");
    const undo = help.commands.find((c) => c.id === "ed:undo")!;
    expect(undo.active).toBe(true);
    expect(undo.chords).toContain("M-/");
  });

  /* ── Conditional consumption (the blocker-2 fix) ───────────────────────
   * A command whose action reports a no-op (returns `false`) must NOT
   * swallow the matched key, so native browser behavior is preserved for
   * state-conditional commands (deselect/delete/nudge with no actionable
   * selection). A command that consumed (void/true) still swallows it.
   * This is the framework-level regression test from the figrecipe owner
   * card scitex-ui-keymap-conditional-consumption-20260916.
   */

  it("consumes the key when the matched command has an actionable effect (backwards-compatible)", () => {
    const run = vi.fn(() => {
      /* returns void -> consumed, exactly like every pre-fix action */
    });
    reg.set({ id: "remove", label: "Remove", action: run });
    expect(map.bind("global", "del", "remove")).toBeNull();
    const ev = key({ key: "Delete" });
    map["handleKeydown"](ev as any);
    expect(run).toHaveBeenCalledTimes(1);
    expect(ev._prevented.called).toBe(true); // always-actionable: swallowed
  });

  it("does NOT consume the key when the matched command is a no-op (returns false)", () => {
    const run = vi.fn(() => false); // nothing selected -> no-op
    reg.set({ id: "remove", label: "Remove", action: run });
    expect(map.bind("global", "del", "remove")).toBeNull();
    const ev = key({ key: "Delete" });
    map["handleKeydown"](ev as any);
    expect(run).toHaveBeenCalledTimes(1); // action WAS still invoked
    expect(ev._prevented.called).toBe(false); // but native Delete is preserved
  });

  it("does NOT consume for a mode-inactive command even when bound", () => {
    const run = vi.fn();
    reg.set({ id: "ed:remove", label: "Remove", action: run, modes: new Set(["editor"]) });
    expect(map.bind("editor", "del", "ed:remove")).toBeNull();
    // No mode active -> the command is inactive -> not consumed.
    const ev = key({ key: "Delete" });
    map["handleKeydown"](ev as any);
    expect(run).not.toHaveBeenCalled();
    expect(ev._prevented.called).toBe(false);
  });

  it("registry.run() reports the consumption signal callers gate preventDefault on", () => {
    const noop = vi.fn(() => false);
    const consume = vi.fn(); // void
    reg.set({ id: "noop", label: "Noop", action: noop });
    reg.set({ id: "consume", label: "Consume", action: consume });
    expect(reg.run("noop", { via: "keyboard" })).toBe(false);
    expect(reg.run("consume", { via: "keyboard" })).toBe(true);
    expect(reg.run("missing", { via: "keyboard" })).toBe(false);
  });
});

/* ── Keymap overrides — the write-only defect (setOverride was ignored) ──────
 * 0.22.0 wrote overrideStorage but resolve()/findBindingByChord()/help() and
 * dispatch never read it, so a persisted user override had NO runtime effect
 * (a Hub settings UI could save a shortcut that does nothing). These are the
 * framework regression tests for that fix — they RED on 0.22.0 and GREEN on
 * the override-consultation fix. They cover every acceptance criterion on the
 * card: override changes keyboard + program dispatch; conflict detection sees
 * the effective scope; unbind/enable/reset restore correct defaults; help
 * reports effective chords; global-vs-mode precedence + input suppression
 * remain; and the persistence adapter round-trips pure-JSON override data.
 */
describe("Keymap overrides (write-only defect fix)", () => {
  let reg: CommandRegistry;
  let map: Keymap;

  beforeEach(() => {
    document.body.innerHTML = "";
    reg = new CommandRegistry();
    map = new Keymap({ registry: reg });
  });

  it("an override redirects keyboard dispatch to the new chord and frees the old one", () => {
    const save = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    map.setOverride("save", "M-s"); // alt+s

    const fired = key({ key: "s", alt: true });
    map["handleKeydown"](fired as any);
    expect(save).toHaveBeenCalledTimes(1); // M-s now runs save
    expect(fired._prevented.called).toBe(true);

    const old = key({ key: "s", ctrl: true });
    map["handleKeydown"](old as any);
    expect(save).toHaveBeenCalledTimes(1); // C-s no longer runs save
    expect(old._prevented.called).toBe(false); // the freed chord: native behavior preserved
  });

  it("an override redirects program dispatch (dispatchSequence) too", () => {
    const save = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    map.setOverride("save", "M-s");

    expect(map.dispatchSequence("M-s", "program")).toBe("save");
    expect(save).toHaveBeenCalledTimes(1);
    expect(map.dispatchSequence("C-s", "program")).toBeNull(); // displaced chord is free
  });

  it("help() reports the EFFECTIVE chord after an override, not the displaced default", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    map.setOverride("save", "M-s");

    const saveHelp = map.help().commands.find((c) => c.id === "save")!;
    expect(saveHelp.chords).toContain("M-S");
    expect(saveHelp.chords).not.toContain("C-S");
  });

  it("binding a chord that is effectively occupied by an override is a conflict", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    map.setOverride("save", "C-c"); // save now effectively at C-c (was a free chord)

    // close tries to take C-c — it is effectively occupied by save's override.
    const conflict = map.bind("global", "C-c", "close");
    expect(conflict).not.toBeNull();
    expect(conflict!.existingCommandId).toBe("save");
    expect(conflict!.newCommandId).toBe("close");
  });

  it("an override-induced collision is surfaced via overrideConflicts() (not silent)", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("global", "C-c", "close")).toBeNull();
    map.setOverride("save", "C-c"); // save's override lands on close's default chord

    const conflicts = map.overrideConflicts();
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].scope).toBe("global");
    expect(conflicts[0].sequenceKey).toBe("C-C");
    expect([conflicts[0].existingCommandId, conflicts[0].newCommandId]).toEqual(
      expect.arrayContaining(["save", "close"]),
    );
  });

  it("an occupied override has one winner for keyboard, program dispatch and help", () => {
    const save = vi.fn();
    const close = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    reg.set({ id: "close", label: "Close", action: close });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("global", "C-c", "close")).toBeNull();
    expect(map.bind("global", "C-w", "close")).toBeNull();
    map.setOverride("save", "C-c");

    const event = dispatchKey(map, { key: "c", ctrlKey: true });
    expect(event.defaultPrevented).toBe(true);
    expect(save).toHaveBeenCalledTimes(1);
    expect(close).not.toHaveBeenCalled();
    expect(map.dispatchSequence("C-c", "program")).toBe("save");
    expect(save).toHaveBeenCalledTimes(2);
    expect(close).not.toHaveBeenCalled();
    expect(map.help().commands.find((c) => c.id === "save")!.chords).toEqual(["C-C"]);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual(["C-W"]);
    expect(map.overrideConflicts()).toEqual([{
      sequenceKey: "C-C", scope: "global", existingCommandId: "close", newCommandId: "save",
    }]);

    expect(dispatchKey(map, { key: "s", ctrlKey: true }).defaultPrevented).toBe(false);
    expect(map.dispatchSequence("C-s")).toBeNull();
    expect(save).toHaveBeenCalledTimes(2);
    expect(dispatchKey(map, { key: "w", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(close).toHaveBeenCalledTimes(1); // its other factory chord survives
  });

  it.each([true, false])("uses the collision winner's input eligibility (%s)", (inInput) => {
    const save = vi.fn();
    const close = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    reg.set({ id: "close", label: "Close", action: close });
    expect(map.bind("global", "C-s", "save", inInput)).toBeNull();
    expect(map.bind("global", "C-c", "close", !inInput)).toBeNull();
    map.setOverride("save", "C-c");

    const input = document.createElement("input");
    const event = dispatchKey(map, { key: "c", ctrlKey: true }, input);
    expect(event.defaultPrevented).toBe(inInput);
    expect(save).toHaveBeenCalledTimes(inInput ? 1 : 0);
    expect(close).not.toHaveBeenCalled();
    expect(map.dispatchSequence("C-c", "program")).toBe("save");
    expect(save).toHaveBeenCalledTimes(inInput ? 2 : 1);
    expect(close).not.toHaveBeenCalled();
    expect(map.help().commands.find((c) => c.id === "save")!.chords).toEqual(["C-C"]);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual([]);
  });

  it.each([
    ["z-first", "a-last"],
    ["a-last", "z-first"],
  ])("keeps conflicting overrides deterministic when set %s then %s", (first, second) => {
    const firstAction = vi.fn();
    const lastAction = vi.fn();
    reg.set({ id: "z-first", label: "First bound", action: firstAction });
    reg.set({ id: "a-last", label: "Last bound", action: lastAction });
    expect(map.bind("global", "C-s", "z-first")).toBeNull();
    expect(map.bind("global", "M-s", "z-first")).toBeNull();
    expect(map.bind("global", "C-c", "a-last")).toBeNull();
    map.setOverride(first, "C-q");
    map.setOverride(second, "C-q");

    expect(dispatchKey(map, { key: "q", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(map.dispatchSequence("C-q", "program")).toBe("a-last");
    expect(lastAction).toHaveBeenCalledTimes(2);
    expect(firstAction).not.toHaveBeenCalled();
    expect(map.help().commands.find((c) => c.id === "z-first")!.chords).toEqual([]);
    expect(map.help().commands.find((c) => c.id === "a-last")!.chords).toEqual(["C-Q"]);
    const conflicts = [{
      sequenceKey: "C-Q", scope: "global", existingCommandId: "z-first", newCommandId: "a-last",
    }];
    expect(map.overrideConflicts()).toEqual(conflicts);

    // Persistence input order does not change the factory binding order's winner.
    map.loadOverrides({ overrides: { [second]: "C-q", [first]: "C-q" } });
    expect(dispatchKey(map, { key: "q", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(map.dispatchSequence("C-q", "program")).toBe("a-last");
    expect(lastAction).toHaveBeenCalledTimes(4);
    expect(firstAction).not.toHaveBeenCalled();
    expect(map.overrideConflicts()).toEqual(conflicts);
    expect(map.help().commands.find((c) => c.id === "z-first")!.chords).toEqual([]);
    expect(map.help().commands.find((c) => c.id === "a-last")!.chords).toEqual(["C-Q"]);
  });

  it("restores displaced bindings after unbind, enable and reset", () => {
    const save = vi.fn();
    const close = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    reg.set({ id: "close", label: "Close", action: close });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("global", "C-c", "close")).toBeNull();
    map.setOverride("save", "C-c");

    map.unbind("close");
    expect(map.overrideConflicts()).toEqual([]);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual([]);
    expect(dispatchKey(map, { key: "c", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(save).toHaveBeenCalledTimes(1);
    expect(close).not.toHaveBeenCalled();

    map.enable("close");
    expect(map.overrideConflicts()).toHaveLength(1);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual([]);
    expect(map.dispatchSequence("C-c")).toBe("save");
    expect(save).toHaveBeenCalledTimes(2);

    map.unbind("save"); // also removes save's override, so close regains C-c
    expect(map.overrideConflicts()).toEqual([]);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual(["C-C"]);
    expect(dispatchKey(map, { key: "c", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(close).toHaveBeenCalledTimes(1);
    map.enable("save");
    expect(map.dispatchSequence("C-s")).toBe("save"); // factory chord, not the removed override
    expect(map.dispatchSequence("C-c")).toBe("close");

    map.setOverride("save", "C-c");
    map.resetOverrides();
    expect(map.overrideConflicts()).toEqual([]);
    expect(map.help().commands.find((c) => c.id === "save")!.chords).toEqual(["C-S"]);
    expect(map.help().commands.find((c) => c.id === "close")!.chords).toEqual(["C-C"]);
    expect(dispatchKey(map, { key: "s", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(dispatchKey(map, { key: "c", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(save).toHaveBeenCalledTimes(4);
    expect(close).toHaveBeenCalledTimes(3);
  });

  it("help hides only mode-shadowed chords and restores them as ownership changes", () => {
    const globalSave = vi.fn();
    const editorSave = vi.fn();
    reg.set({ id: "global-save", label: "Global save", action: globalSave });
    reg.set({ id: "editor-save", label: "Editor save", action: editorSave, modes: new Set(["editor"]) });
    expect(map.bind("global", "C-s", "global-save")).toBeNull();
    expect(map.bind("global", "C-p", "global-save")).toBeNull();
    expect(map.bind("editor", "C-s", "editor-save")).toBeNull();
    map.activateMode("editor");

    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-P"]);
    expect(map.help().commands.find((c) => c.id === "editor-save")!).toMatchObject({ active: true, chords: ["C-S"] });
    expect(dispatchKey(map, { key: "s", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(map.dispatchSequence("C-s")).toBe("editor-save");
    expect(editorSave).toHaveBeenCalledTimes(2);
    expect(globalSave).not.toHaveBeenCalled();
    expect(dispatchKey(map, { key: "p", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(globalSave).toHaveBeenCalledTimes(1);

    map.setOverride("editor-save", "M-e");
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-S", "C-P"]);
    expect(map.help().commands.find((c) => c.id === "editor-save")!.chords).toEqual(["M-E"]);
    expect(map.dispatchSequence("C-s")).toBe("global-save");
    expect(map.dispatchSequence("M-e")).toBe("editor-save");
    map.resetOverrides();
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-P"]);

    map.unbind("editor-save");
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-S", "C-P"]);
    expect(map.help().commands.find((c) => c.id === "editor-save")!.chords).toEqual([]);
    expect(map.dispatchSequence("C-s")).toBe("global-save");
    map.enable("editor-save");
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-P"]);

    map.deactivateMode();
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-S", "C-P"]);
    expect(map.help().commands.find((c) => c.id === "editor-save")!).toMatchObject({ active: false, chords: [] });
    expect(dispatchKey(map, { key: "s", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(globalSave).toHaveBeenCalledTimes(4);
    map.activateMode("editor");
    expect(map.help().commands.find((c) => c.id === "global-save")!.chords).toEqual(["C-P"]);
    expect(dispatchKey(map, { key: "s", ctrlKey: true }).defaultPrevented).toBe(true);
    expect(editorSave).toHaveBeenCalledTimes(4);
  });

  it("unbind disables a command (its default is preserved) and enable restores it", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();

    map.unbind("save");
    expect(map.resolve(parseSequence("C-s"))).toBeNull(); // disabled: no longer bound
    expect(map.dispatchSequence("C-s", "program")).toBeNull();
    expect(map.help().commands.find((c) => c.id === "save")!.chords).toEqual([]);

    map.enable("save");
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("save"); // restored
    expect(map.help().commands.find((c) => c.id === "save")!.chords).toContain("C-S");
  });

  it("resetOverrides restores factory defaults after overrides AND unbinds", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("global", "C-c", "close")).toBeNull();

    map.setOverride("save", "M-s");
    map.unbind("close");

    map.resetOverrides();

    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("save"); // override cleared
    expect(map.resolve(parseSequence("M-s"))).toBeNull();
    expect(map.resolve(parseSequence("C-c"))!.commandId).toBe("close"); // unbind restored
    expect(map.overrideConflicts()).toEqual([]);
  });

  it("global vs active-mode precedence is preserved when overrides are present", () => {
    reg.set({ id: "global-s", label: "G", action: vi.fn() });
    reg.set({ id: "editor-s", label: "E", action: vi.fn() });
    expect(map.bind("global", "C-s", "global-s")).toBeNull();
    expect(map.bind("editor", "C-s", "editor-s")).toBeNull();
    expect(map.bind("editor", "C-x", "editor-s")).toBeNull();

    map.activateMode("editor");
    // shadowing unchanged: the editor binding wins at C-s
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("editor-s");

    // override the editor command onto a fresh chord; it applies only in editor scope
    map.setOverride("editor-s", "M-e");
    expect(map.resolve(parseSequence("M-e"))!.commandId).toBe("editor-s");
    expect(map.resolve(parseSequence("C-x"))).toBeNull(); // C-x displaced in editor

    map.deactivateMode();
    // global scope: editor-s is gone, global-s is still at C-s
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("global-s");
    expect(map.resolve(parseSequence("M-e"))).toBeNull(); // editor-only override not visible
  });

  it("input suppression still applies to a command reached via its override", () => {
    const copy = vi.fn();
    reg.set({ id: "copy", label: "Copy", action: copy });
    expect(map.bind("global", "C-c", "copy")).toBeNull(); // inInput=false (default)
    map.setOverride("copy", "M-c"); // moved to alt+c, still a non-input binding

    const input = document.createElement("input");
    document.body.appendChild(input);
    map["handleKeydown"](key({ key: "c", alt: true, target: input }) as any);
    expect(copy).not.toHaveBeenCalled(); // suppressed inside the field via the override chord
  });

  it("serializeOverrides()/loadOverrides() round-trip pure-JSON persistence data", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("global", "C-c", "close")).toBeNull();

    map.setOverride("save", "M-s");
    map.unbind("close");

    const data = map.serializeOverrides();
    // must be pure JSON — the persistence adapter's contract (Hub stores this verbatim)
    const roundTripped = JSON.parse(JSON.stringify(data));
    expect(roundTripped).toEqual(data);
    expect(roundTripped).toEqual({ overrides: { save: "M-S" }, unbound: ["close"] });

    // a fresh app with the same defaults, restored from that JSON:
    const reg2 = new CommandRegistry();
    reg2.set({ id: "save", label: "Save", action: vi.fn() });
    reg2.set({ id: "close", label: "Close", action: vi.fn() });
    const map2 = new Keymap({ registry: reg2 });
    expect(map2.bind("global", "C-s", "save")).toBeNull();
    expect(map2.bind("global", "C-c", "close")).toBeNull();
    map2.loadOverrides(roundTripped);

    expect(map2.resolve(parseSequence("M-s"))!.commandId).toBe("save"); // override restored
    expect(map2.resolve(parseSequence("C-s"))).toBeNull(); // displaced
    expect(map2.resolve(parseSequence("C-c"))).toBeNull(); // close disabled
    expect(map2.help().commands.find((c) => c.id === "save")!.chords).toContain("M-S");
  });

  it("the overrideStorage constructor seam seeds initial overrides", () => {
    const save = vi.fn();
    reg.set({ id: "save", label: "Save", action: save });
    const seeded = new Keymap({ registry: reg, overrideStorage: new Map([["save", parseSequence("M-s")]]) });
    expect(seeded.bind("global", "C-s", "save")).toBeNull();
    expect(seeded.resolve(parseSequence("M-s"))!.commandId).toBe("save");
    expect(seeded.resolve(parseSequence("C-s"))).toBeNull();
  });
});

describe("Keymap composition and event ownership", () => {
  let registry: CommandRegistry;
  let map: Keymap;
  let target: HTMLElement;
  let detach: () => void;

  beforeEach(() => {
    registry = new CommandRegistry();
    map = new Keymap({ registry });
    // An isolated event tree exercises the attached listener without unrelated
    // document shortcuts participating in these event-ownership controls.
    target = document.createElement("div");
    detach = map.attach(target);
  });

  afterEach(() => detach());

  const guardedCases: Array<{
    name: string;
    chord: string;
    init: KeyboardEventInit;
    legacyField?: "keyCode" | "which";
    altGraph?: boolean;
    prevented?: boolean;
  }> = [
    { name: "isComposing", chord: "C-s", init: { key: "s", ctrlKey: true, isComposing: true } },
    { name: "legacy keyCode 229", chord: "C-s", init: { key: "s", ctrlKey: true }, legacyField: "keyCode" },
    { name: "legacy which 229", chord: "C-s", init: { key: "s", ctrlKey: true }, legacyField: "which" },
    { name: "Dead", chord: "C-Dead", init: { key: "Dead", ctrlKey: true } },
    { name: "Process", chord: "C-Process", init: { key: "Process", ctrlKey: true } },
    { name: "held AltGraph", chord: "C-M-s", init: { key: "s", ctrlKey: true, altKey: true }, altGraph: true },
    { name: "AltGraph modifier", chord: "AltGraph", init: { key: "AltGraph" } },
    { name: "already prevented", chord: "C-s", init: { key: "s", ctrlKey: true }, prevented: true },
  ];

  it.each(guardedCases)("ignores $name and cancels an existing prefix", (scenario) => {
    const single = vi.fn();
    const completedPrefix = vi.fn();
    const stalePrefix = vi.fn();
    const ordinary = vi.fn();
    registry.set({ id: "single", label: "Single", action: single });
    registry.set({ id: "completed-prefix", label: "Completed prefix", action: completedPrefix });
    registry.set({ id: "stale-prefix", label: "Stale prefix", action: stalePrefix });
    registry.set({ id: "ordinary", label: "Ordinary", action: ordinary });
    map.bind("global", scenario.chord, "single", true);
    map.bind("global", `C-x ${scenario.chord}`, "completed-prefix", true);
    map.bind("global", "C-x C-f", "stale-prefix", true);
    map.bind("global", "C-f", "ordinary", true);

    const blockedEvent = () => {
      const event = new KeyboardEvent("keydown", { ...scenario.init, bubbles: true, cancelable: true });
      if (scenario.legacyField) Object.defineProperty(event, scenario.legacyField, { value: 229 });
      if (scenario.altGraph) Object.defineProperty(event, "getModifierState", { value: (name: string) => name === "AltGraph" });
      if (scenario.prevented) event.preventDefault();
      const prevent = vi.spyOn(event, "preventDefault");
      target.dispatchEvent(event);
      return { event, prevent };
    };

    const first = blockedEvent();
    const prefix = new KeyboardEvent("keydown", { key: "x", ctrlKey: true, bubbles: true, cancelable: true });
    target.dispatchEvent(prefix);
    const second = blockedEvent();
    const next = new KeyboardEvent("keydown", { key: "f", ctrlKey: true, bubbles: true, cancelable: true });
    target.dispatchEvent(next);

    expect({
      single: single.mock.calls.length,
      completedPrefix: completedPrefix.mock.calls.length,
      stalePrefix: stalePrefix.mock.calls.length,
      ordinary: ordinary.mock.calls.length,
      firstPreventCalls: first.prevent.mock.calls.length,
      secondPreventCalls: second.prevent.mock.calls.length,
      blockedDefaultPrevented: [first.event.defaultPrevented, second.event.defaultPrevented],
      prefixPrevented: prefix.defaultPrevented,
      ordinaryPrevented: next.defaultPrevented,
    }).toEqual({
      single: 0, completedPrefix: 0, stalePrefix: 0, ordinary: 1,
      firstPreventCalls: 0, secondPreventCalls: 0,
      blockedDefaultPrevented: [!!scenario.prevented, !!scenario.prevented],
      prefixPrevented: true, ordinaryPrevented: true,
    });
  });

  it.each(["div", "input", "textarea", "contenteditable", "plaintext-only"])(
    "preserves composing text in %s even when its binding opts into inputs",
    (kind) => {
      const action = vi.fn();
      registry.set({ id: "save", label: "Save", action });
      map.bind("global", "C-s", "save", true);
      const editor = document.createElement(kind === "contenteditable" || kind === "plaintext-only" ? "div" : kind);
      if (kind === "contenteditable" || kind === "plaintext-only") editor.setAttribute("contenteditable", kind === "contenteditable" ? "true" : kind);
      target.appendChild(editor);

      editor.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
      // Some IME keydowns omit the flag; the composition lifecycle still owns it.
      const composing = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true, cancelable: true });
      editor.dispatchEvent(composing);
      editor.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
      const ordinary = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true, cancelable: true });
      editor.dispatchEvent(ordinary);

      expect({ calls: action.mock.calls.length, composingPrevented: composing.defaultPrevented, ordinaryPrevented: ordinary.defaultPrevented })
        .toEqual({ calls: 1, composingPrevented: false, ordinaryPrevented: true });
    },
  );

  it("cancels a prefix when composition starts and ends without a keydown", () => {
    const stale = vi.fn();
    const ordinary = vi.fn();
    registry.set({ id: "stale", label: "Stale", action: stale });
    registry.set({ id: "ordinary", label: "Ordinary", action: ordinary });
    map.bind("global", "C-x C-f", "stale");
    map.bind("global", "C-f", "ordinary");
    target.dispatchEvent(new KeyboardEvent("keydown", { key: "x", ctrlKey: true, bubbles: true }));
    target.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    target.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    target.dispatchEvent(new KeyboardEvent("keydown", { key: "f", ctrlKey: true, bubbles: true }));
    expect([stale.mock.calls.length, ordinary.mock.calls.length]).toEqual([0, 1]);
  });

  it("detaches composition listeners before reattaching the same keymap", () => {
    const action = vi.fn();
    registry.set({ id: "save", label: "Save", action });
    map.bind("global", "C-s", "save");
    detach();
    target.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    detach = map.attach(target);
    target.dispatchEvent(new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true }));
    expect(action).toHaveBeenCalledTimes(1);
  });
});

describe("Keymap factory presence and override prefix conflicts", () => {
  let registry: CommandRegistry;
  let map: Keymap;

  beforeEach(() => {
    registry = new CommandRegistry();
    map = new Keymap({ registry });
    registry.set({ id: "a", label: "A", action: vi.fn() });
    registry.set({ id: "b", label: "B", action: vi.fn() });
  });

  it.each([
    { name: "shorter override", other: "C-x C-b", override: "C-x" },
    { name: "longer override", other: "C-x", override: "C-x C-a" },
  ])("reports a $name without changing sequence dispatch", (scenario) => {
    map.bind("global", "M-a", "a");
    map.bind("global", scenario.other, "b");
    map.setOverride("a", scenario.override);
    expect({
      conflicts: map.overrideConflicts(),
      overridden: map.dispatchSequence(scenario.override),
      other: map.dispatchSequence(scenario.other),
    }).toEqual({
      conflicts: [{ sequenceKey: "C-X", scope: "global", existingCommandId: "b", newCommandId: "a" }],
      overridden: "a", other: "b",
    });
  });

  it.each([
    { name: "mode override before global prefix", overrideScope: "editor", otherScope: "global", other: "C-x C-b", override: "C-x" },
    { name: "global override after mode prefix", overrideScope: "global", otherScope: "editor", other: "C-x", override: "C-x C-a" },
  ])("reports $name before the mode is activated", (scenario) => {
    map.bind(scenario.overrideScope, "M-a", "a");
    map.bind(scenario.otherScope, scenario.other, "b");
    map.setOverride("a", scenario.override);
    const beforeActivation = map.overrideConflicts();
    map.activateMode("editor");
    expect({ beforeActivation, afterActivation: map.overrideConflicts() }).toEqual({
      beforeActivation: [{ sequenceKey: "C-X", scope: "editor", existingCommandId: "b", newCommandId: "a" }],
      afterActivation: [{ sequenceKey: "C-X", scope: "editor", existingCommandId: "b", newCommandId: "a" }],
    });
  });

  it("checks future definition modes and excludes commands that cannot be active together", () => {
    registry.set({ id: "a", label: "A", action: vi.fn(), modes: new Set(["editor"]) });
    registry.set({ id: "b", label: "B", action: vi.fn(), modes: new Set(["editor"]) });
    map.bind("global", "M-a", "a");
    map.bind("global", "C-x C-b", "b");
    map.setOverride("a", "C-x");
    const sharedMode = map.overrideConflicts();
    registry.set({ id: "b", label: "B", action: vi.fn(), modes: new Set(["review"]) });
    expect({ sharedMode, separateModes: map.overrideConflicts() }).toEqual({
      sharedMode: [{ sequenceKey: "C-X", scope: "editor", existingCommandId: "b", newCommandId: "a" }],
      separateModes: [],
    });
  });

  it("preserves exact mode shadowing while checking prefix conflicts", () => {
    registry.set({ id: "mode", label: "Mode", action: vi.fn() });
    map.bind("global", "M-a", "a");
    map.bind("global", "C-x C-b", "b");
    map.bind("editor", "C-x", "mode");
    map.setOverride("a", "C-x");
    map.activateMode("editor");
    expect({ conflicts: map.overrideConflicts(), shorter: map.dispatchSequence("C-x") }).toEqual({
      conflicts: [{ sequenceKey: "C-X", scope: "global", existingCommandId: "b", newCommandId: "a" }],
      shorter: "mode",
    });
  });

  it("finds a factory binding when its effective chord is mode-shadowed", () => {
    map.bind("global", "C-s", "a");
    map.bind("editor", "C-s", "b");
    map.activateMode("editor");
    expect({ chords: map.help().commands.find((command) => command.id === "a")!.chords, factory: map.hasFactoryBinding("a"), missing: map.hasFactoryBinding("missing") })
      .toEqual({ chords: [], factory: true, missing: false });
  });

  it("retains factory presence after an override displaces or disables a command", () => {
    map.bind("global", "M-a", "a");
    map.bind("global", "C-s", "b");
    map.setOverride("a", "C-s");
    const displaced = { chords: map.help().commands.find((command) => command.id === "b")!.chords, factory: map.hasFactoryBinding("b") };
    map.unbind("b");
    expect({ displaced, disabled: map.hasFactoryBinding("b"), stillBound: map.hasFactoryBinding("a") }).toEqual({
      displaced: { chords: [], factory: true }, disabled: true, stillBound: true,
    });
  });

  it("reports no new conflict for factory prefixes and preserves their keyboard dispatch", () => {
    const shorter = vi.fn();
    const longer = vi.fn();
    registry.set({ id: "a", label: "A", action: shorter });
    registry.set({ id: "b", label: "B", action: longer });
    map.bind("global", "C-x", "a");
    map.bind("global", "C-x C-b", "b");
    const target = document.createElement("div");
    const detach = map.attach(target);
    try {
      target.dispatchEvent(new KeyboardEvent("keydown", { key: "x", ctrlKey: true, bubbles: true, cancelable: true }));
      target.dispatchEvent(new KeyboardEvent("keydown", { key: "b", ctrlKey: true, bubbles: true, cancelable: true }));
    } finally {
      detach();
    }
    expect({ conflicts: map.overrideConflicts(), shorter: shorter.mock.calls.length, longer: longer.mock.calls.length })
      .toEqual({ conflicts: [], shorter: 1, longer: 0 });
  });
});
