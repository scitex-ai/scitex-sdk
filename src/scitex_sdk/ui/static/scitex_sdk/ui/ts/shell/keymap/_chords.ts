/**
 * Chord grammar and normalization for the keymap primitive.
 *
 * A CHORD is one keystroke: zero or more modifiers plus one key.
 *   C-x   Ctrl + x
 *   M-g   Alt  + g   (Emacs "M" = Meta, which on most keyboards is Alt)
 *   S-A   Shift + A
 *   M2-x  Super/Win/⌘ + x   (Emacs "M2" = Super)
 *   x     bare key, matched case-insensitively for letters
 *   RET / TAB / SPAC / ESC / F1..F12 / UP / DWN / LFT / RGT — named keys
 *   , ; / etc. — punctuation, matched exactly (shift already reflected)
 *
 * A SEQUENCE is a space-separated run of chords — the Emacs prefix-command
 * mechanism:
 *   C-x C-s
 *
 * The canonical chord records modifier flags plus a key in a small closed
 * vocabulary, so the same binding reads identically across layouts: the parser
 * is the normalization point, and matching compares canonical forms.
 */

export interface Chord {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
  /** Canonical key: a lowercase letter, or a named key (see NAMED_KEYS). */
  key: string;
}

export type Sequence = Chord[];

/** The modifier token -> flag, Emacs-faithful (C=Ctrl, M=Alt, S=Shift, M2=Meta). */
const MOD_TOKENS: Record<string, keyof Omit<Chord, "key">> = {
  C: "ctrl",
  M: "alt",
  S: "shift",
  M2: "meta",
};

/** Named-key aliases -> the canonical single-token key. */
const NAMED_KEYS: Record<string, string> = {
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
  end: "end",
};

function bareKey(token: string): string {
  const named = NAMED_KEYS[token.toLowerCase()];
  if (named !== undefined) return named;
  // function keys and punctuation pass through; letters lowercase.
  return token.length === 1 ? token.toLowerCase() : token;
}

/** Parse a single chord such as "C-x", "M2-C-RET", "x". */
export function parseChord(input: string): Chord {
  const chord: Chord = { ctrl: false, alt: false, shift: false, meta: false, key: "" };
  const trimmed = input.trim();
  if (trimmed === "") throw new Error("parseChord: empty chord");
  // Split off modifiers greedily: a chord's modifier part is everything before
  // the final un-hyphenated key. Keys are single tokens that never contain a
  // leading '-' except as the separator, so scan from the front for known
  // MOD tokens joined by '-'.
  let rest = trimmed;
  for (;;) {
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

/** Parse a sequence such as "C-x C-s" into a list of chords. */
export function parseSequence(input: string): Sequence {
  return input.trim().split(/\s+/).filter(Boolean).map(parseChord);
}

/**
 * Render a chord to its canonical display string ("C-x", "M2-C-RET", "x").
 * Deterministic order C, M, S, M2 then the key; the key upper-cases single
 * letters for readability of named/letter chords, keeps punctuation as-is.
 */
export function chordToString(chord: Chord): string {
  const parts: string[] = [];
  if (chord.ctrl) parts.push("C");
  if (chord.alt) parts.push("M");
  if (chord.shift) parts.push("S");
  if (chord.meta) parts.push("M2");
  const key =
    chord.key.length === 1 && /[a-z0-9]/.test(chord.key) ? chord.key.toUpperCase() : chord.key;
  parts.push(key);
  return parts.join("-");
}

/** Stable map key for a sequence — order-sensitive, canonical. */
export function sequenceKey(seq: Sequence): string {
  return seq.map(chordToString).join(" ");
}

/** Two chords match when every modifier flag agrees and the keys agree. */
export function chordMatches(a: Chord, b: Chord): boolean {
  return (
    a.ctrl === b.ctrl &&
    a.alt === b.alt &&
    a.shift === b.shift &&
    a.meta === b.meta &&
    a.key === b.key
  );
}

interface KeyChordSource {
  key: string;
  code?: string;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
}

/**
 * Build the canonical chord for a browser KeyboardEvent (or a stand-in with the
 * same fields — the vitest harness uses these fakes).
 *
 * Returns null for keys the keymap should never treat as a command chord:
 * bare modifier presses (Shift/Ctrl/Alt/Win on their own) and the dead keys
 * where `event.key === "Unidentified"`.
 *
 * LETTERS match case-insensitively (the modifier flags carry the meaning), so
 * "C-x" and a real Ctrl+X both canonicalize to the same chord. PUNCTUATION is
 * taken from `event.key` verbatim, which already reflects Shift — so a chord
 * written "S-," (shift+comma) matches the actual "," keydown only when that
 * keydown's shift flag lines up with what produced it; in practice apps bind
 * the punctuation they want to appear, e.g. "C-," for ctrl+comma.
 */
export function eventToChord(event: KeyChordSource): Chord | null {
  const raw = event.key;
  if (raw === "Unidentified") return null;
  // Bare modifier keys: no command intent.
  if (["Shift", "Control", "Alt", "Meta", "CapsLock"].includes(raw)) return null;
  const named = NAMED_KEYS[raw.toLowerCase()];
  const isLetter = /^[a-zA-Z]$/.test(raw);
  const key = named !== undefined ? named : isLetter ? raw.toLowerCase() : raw;
  return {
    ctrl: event.ctrlKey,
    alt: event.altKey,
    shift: event.shiftKey,
    meta: event.metaKey,
    key,
  };
}

/**
 * Does this event's chord EXTEND a bound prefix? Pure: used by the runtime to
 * decide whether to keep a pending sequence alive. `bound` is the set of all
 * sequence keys the runtime knows about.
 */
export function isPrefixOfAnyBound(pending: Sequence, boundKeys: ReadonlySet<string>): boolean {
  const prefix = sequenceKey(pending);
  for (const bound of boundKeys) {
    if (bound === prefix) continue;
    if (bound.startsWith(prefix + " ")) return true;
  }
  return false;
}
