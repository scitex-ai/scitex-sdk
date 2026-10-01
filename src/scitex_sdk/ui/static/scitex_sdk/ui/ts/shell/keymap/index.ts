/**
 * The keymap primitive — public surface.
 *
 * Build one Keymap (usually per page/app) against a CommandRegistry, bind
 * chords to command IDs, attach() for keyboard, dispatchSequence() for
 * button/agent, and help() for the introspection model.
 */
export { CommandRegistry, globalRegistry } from "./_registry";
export type { CallerInfo, CommandDef, CommandHandle } from "./_registry";
export { Keymap } from "./_keymap";
export type { Binding, BindingScope, Conflict, KeymapOptions } from "./_keymap";
export {
  parseChord,
  parseSequence,
  chordToString,
  sequenceKey,
  chordMatches,
  eventToChord,
  isPrefixOfAnyBound,
} from "./_chords";
export type { Chord, Sequence } from "./_chords";
