/**
 * Shell terminal — barrel export.
 */

export {
  initTerminal,
  loadXtermModules,
  loadXtermCSS,
} from "./_TerminalFactory";
export { processOscEscapes, createDefaultOscHandlers } from "./_OscHandler";
export type { OscHandlerEntry, OscCallback } from "./_OscHandler";
export type {
  TerminalInstance,
  TerminalConnectionAdapter,
  TerminalConfig,
} from "./types";
