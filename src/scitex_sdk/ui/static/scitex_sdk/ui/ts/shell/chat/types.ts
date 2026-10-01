/**
 * Shell chat types — adapter interface for backend abstraction.
 */

/** Backend adapter for AI chat. */
export interface ChatAdapter {
  /** Send a chat message and return the SSE Response. */
  streamChat(
    message: string,
    context?: AiContext,
    images?: string[],
  ): Promise<Response>;

  /** Optional: fetch current model info. */
  fetchCurrentModel?(): Promise<{
    model: string;
    display?: string;
    campaign?: boolean;
  } | null>;

  /** Optional: speak text via backend TTS. */
  speak?(text: string): void;
}

/** Context about the active project/environment. */
export interface AiContext {
  username?: string;
  slug?: string;
  [key: string]: unknown;
}

/** A stored chat message. */
export interface StoredMessage {
  role: "user" | "assistant" | "error";
  text: string;
  toolsUsed?: string[];
  media?: MediaRef[];
}

/** Media reference from AI tool results. */
export interface MediaRef {
  type: string;
  path: string;
  ext?: string;
  url?: string;
}

/** Context passed to the stream processor. */
export interface StreamContext {
  messagesEl: HTMLElement;
  modelBadge: HTMLElement | null;
  speak: (text: string) => void;
  autoSpeak: boolean;
  scrollIfNeeded?: () => void;
}

export interface ChatConfig {
  /** Container for chat messages (default: "#stx-shell-ai-messages") */
  messagesContainer?: string | HTMLElement;

  /** Chat input textarea (default: "#stx-shell-ai-input") */
  inputElement?: string | HTMLElement;

  /** Model badge element (default: ".stx-shell-ai-model-badge") */
  modelBadge?: string | HTMLElement;

  /** Backend adapter. */
  adapter: ChatAdapter;

  /** Auto-speak responses (default: false) */
  autoSpeak?: boolean;

  /** Refresh file tree after file operations (default: true) */
  refreshTreeOnFileOps?: boolean;
}
