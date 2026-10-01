/**
 * Shell auto-response — barrel export.
 *
 * Claude Code CLI auto-accept: detects permission prompts in terminal
 * and automatically responds. Pure frontend, no backend needed.
 */

export { AutoResponseManager } from "./_AutoResponseManager";
export type { AutoResponseConfig } from "./_auto-response-config";
export { DEFAULT_CONFIG } from "./_auto-response-config";
export {
  detectState,
  readTerminalBuffer,
  DETECTION_BUFFER_SIZE,
} from "./_claude-state-detector";
export type { ClaudeState } from "./_claude-state-detector";
