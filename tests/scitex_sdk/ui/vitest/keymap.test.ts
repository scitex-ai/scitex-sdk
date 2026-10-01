/**
 * Keymap primitive: chord parsing, registry dispatch, runtime behaviour
 * (mode shadowing, input suppression, prefix expiry, lifecycle), and the
 * help() introspection model. `npx vitest run`
 *
 * The harness drives Keymap.handleKeydown through attach(document) and
 * dispatches plain objects that carry the keyboard fields — no real
 * KeyboardEvent is constructed, so the suite is portable across jsdom
 * versions and workers.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

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
