/**
 * Shell terminal types — adapter interface for connection abstraction.
 *
 * Consumers provide connection adapters for their specific backend:
 *  - Standalone apps: ws://127.0.0.1:{port+1}/
 *  - scitex-cloud: wss://{host}/ws/console/terminal/?project_id={id}
 */

export interface TerminalInstance {
  terminal: any;
  fitAddon: any;
  ws: WebSocket | null;
  connected: boolean;
  resizeObserver: ResizeObserver | null;
  resizeTimeout: ReturnType<typeof setTimeout> | null;
}

/**
 * Connection adapter — provides the WebSocket URL and optional hooks.
 */
export interface TerminalConnectionAdapter {
  /** Return the WebSocket URL to connect to. */
  getWebSocketUrl(): string;

  /** Called when connection status changes. */
  onStatusChange?(
    state: "connecting" | "connected" | "disconnected" | "error",
  ): void;

  /** Process incoming data before writing to terminal (e.g., OSC escapes). */
  onMessage?(data: string, inst: TerminalInstance): string | null;
}

export interface TerminalConfig {
  /** Container element or CSS selector (default: "#stx-shell-ai-console-terminal") */
  container?: string | HTMLElement;

  /** Connection adapter. */
  adapter: TerminalConnectionAdapter;

  /** Enable clipboard handling: Ctrl+C copy, Ctrl+V paste (default: true) */
  clipboard?: boolean;

  /** Enable drag-drop file handling (default: false — requires upload backend) */
  dragDrop?: boolean;

  /** Upload handler for drag-drop files (required if dragDrop is true) */
  onFileDrop?: (files: FileList) => Promise<string[]>;

  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;

  /** Auto-initialize on construction (default: true) */
  autoInit?: boolean;
}
