/**
 * Aggregate ShellConfig — combines all adapter interfaces.
 *
 * Consumers pass a single config object to initShell() to wire everything.
 */

import type { FileTreeAdapter, ShellFileTreeConfig } from "./file-tree/types";
import type { ToolbarConfig } from "./toolbar/types";
import type {
  TerminalConnectionAdapter,
  TerminalConfig,
} from "./terminal/types";
import type { ChatAdapter, ChatConfig } from "./chat/types";
import type { ViewerAdapter, ViewerConfig } from "./viewer/types";

export interface ShellConfig {
  /** File tree configuration (optional — omit to leave file tree empty). */
  fileTree?: {
    adapter: FileTreeAdapter;
    onFileSelect?: ShellFileTreeConfig["onFileSelect"];
    showHidden?: boolean;
    extensions?: string[] | null;
  };

  /** Terminal configuration (optional — omit to skip terminal). */
  terminal?: {
    adapter: TerminalConnectionAdapter;
    clipboard?: boolean;
    dragDrop?: boolean;
    onFileDrop?: TerminalConfig["onFileDrop"];
    reconnectDelay?: number;
  };

  /** Toolbar configuration (optional). */
  toolbar?: ToolbarConfig;

  /** Chat configuration (optional — omit to leave chat static). */
  chat?: {
    adapter: ChatAdapter;
    autoSpeak?: boolean;
  };

  /** Viewer configuration (optional — omit to leave viewer empty). */
  viewer?: {
    adapter: ViewerAdapter;
    onFileOpen?: ViewerConfig["onFileOpen"];
  };
}
