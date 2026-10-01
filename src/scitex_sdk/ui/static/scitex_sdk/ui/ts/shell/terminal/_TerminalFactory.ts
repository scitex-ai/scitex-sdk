/**
 * TerminalFactory — unified terminal creation for shell.
 *
 * Merges standalone-terminal.ts (local vendor, port+1 WebSocket) with
 * console-terminal-factory.ts (OSC escapes, clipboard, drag-drop, zoom).
 *
 * Uses TerminalConnectionAdapter for backend abstraction:
 *  - Standalone: getWebSocketUrl() → ws://127.0.0.1:{port+1}/
 *  - scitex-cloud: getWebSocketUrl() → wss://{host}/ws/console/terminal/?project_id={id}
 */

import type {
  TerminalInstance,
  TerminalConfig,
  TerminalConnectionAdapter,
} from "./types";
import { processOscEscapes, createDefaultOscHandlers } from "./_OscHandler";
import type { OscHandlerEntry } from "./_OscHandler";

/* ── xterm.js loader (local vendor + CDN fallback) ──── */

const XTERM_JS_LOCAL = "/static/scitex_sdk/ui/vendor/xterm/xterm.js";
const XTERM_CSS_LOCAL = "/static/scitex_sdk/ui/vendor/xterm/xterm.css";
const FIT_ADDON_LOCAL = "/static/scitex_sdk/ui/vendor/xterm/xterm-addon-fit.js";
const XTERM_JS_CDN = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js";
const XTERM_CSS_CDN = "https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css";
const FIT_ADDON_CDN =
  "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js";

let cachedTerminal: any = null;
let cachedFitAddon: any = null;

async function fetchWithFallback(local: string, cdn: string): Promise<string> {
  try {
    const resp = await fetch(local);
    if (resp.ok) return resp.text();
  } catch {
    /* local not available */
  }
  return fetch(cdn).then((r) => r.text());
}

export async function loadXtermModules(): Promise<{
  Terminal: any;
  FitAddon: any;
}> {
  if (cachedTerminal)
    return { Terminal: cachedTerminal, FitAddon: cachedFitAddon };

  const win = window as any;
  const [xtermCode, fitCode] = await Promise.all([
    fetchWithFallback(XTERM_JS_LOCAL, XTERM_JS_CDN),
    fetchWithFallback(FIT_ADDON_LOCAL, FIT_ADDON_CDN),
  ]);

  const savedDefine = win.define;
  const savedRequire = win.require;
  win.define = undefined;
  win.require = undefined;
  try {
    new Function(xtermCode)();
    new Function(fitCode)();
  } finally {
    win.define = savedDefine;
    win.require = savedRequire;
  }

  cachedTerminal = win.Terminal?.Terminal || win.Terminal;
  cachedFitAddon = win.FitAddon?.FitAddon || win.FitAddon;
  return { Terminal: cachedTerminal, FitAddon: cachedFitAddon };
}

export function loadXtermCSS(): void {
  if (document.querySelector('link[href*="xterm.css"]')) return;
  const el = document.createElement("link");
  el.rel = "stylesheet";
  el.href = XTERM_CSS_LOCAL;
  el.onerror = () => {
    el.href = XTERM_CSS_CDN;
  };
  document.head.appendChild(el);
}

function getTerminalTheme(): Record<string, string> {
  const s = getComputedStyle(document.documentElement);
  const get = (v: string, fb: string) => s.getPropertyValue(v).trim() || fb;
  const isDark =
    document.documentElement.getAttribute("data-theme") !== "light";
  return isDark
    ? {
        background: get("--terminal-bg", "#0d1117"),
        foreground: get("--terminal-fg", "#c9d1d9"),
        cursor: get("--terminal-cursor", "#58a6ff"),
      }
    : {
        background: get("--terminal-bg", "#ffffff"),
        foreground: get("--terminal-fg", "#24292f"),
        cursor: get("--terminal-cursor", "#0969da"),
      };
}

/* ── Terminal creation ──────────────────────────────── */

export function createTerminalInstance(
  container: HTMLElement,
  TerminalClass: any,
  FitAddonClass: any,
): TerminalInstance {
  const terminal = new TerminalClass({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
    theme: getTerminalTheme(),
    scrollback: 100000,
  });

  terminal.open(container);

  const inst: TerminalInstance = {
    terminal,
    fitAddon: null,
    ws: null,
    connected: false,
    resizeObserver: null,
    resizeTimeout: null,
  };

  if (FitAddonClass) {
    inst.fitAddon = new FitAddonClass();
    terminal.loadAddon(inst.fitAddon);
    fitInstance(inst);

    let lastW = 0;
    let lastH = 0;
    inst.resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (Math.abs(width - lastW) < 2 && Math.abs(height - lastH) < 2) return;
      lastW = width;
      lastH = height;
      if (inst.resizeTimeout) clearTimeout(inst.resizeTimeout);
      inst.resizeTimeout = setTimeout(() => fitInstance(inst), 150);
    });
    inst.resizeObserver.observe(container);
  }

  // User input → WebSocket
  terminal.onData((data: string) => {
    if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send(data);
  });

  return inst;
}

/* ── WebSocket connection ───────────────────────────── */

function sendResize(inst: TerminalInstance): void {
  if (
    inst.ws?.readyState === WebSocket.OPEN &&
    inst.terminal?.rows &&
    inst.terminal?.cols
  ) {
    inst.ws.send(`resize:${inst.terminal.rows}:${inst.terminal.cols}`);
  }
}

export function connectInstance(
  inst: TerminalInstance,
  adapter: TerminalConnectionAdapter,
  oscHandlers: OscHandlerEntry[],
  reconnectDelay: number = 3000,
): void {
  if (inst.connected) return;
  adapter.onStatusChange?.("connecting");

  const url = adapter.getWebSocketUrl();
  console.log(`[TerminalFactory] Connecting to ${url}`);
  inst.ws = new WebSocket(url);

  inst.ws.onopen = () => {
    inst.connected = true;
    adapter.onStatusChange?.("connected");
    sendResize(inst);
    console.log("[TerminalFactory] Connected");
  };

  // Write batching — accumulate WebSocket data and flush via rAF to reduce flicker
  let writeBuf = "";
  let writeRaf = 0;
  inst.ws.onmessage = (ev) => {
    let data: string = ev.data;

    // Adapter-level preprocessing
    if (adapter.onMessage) {
      const processed = adapter.onMessage(data, inst);
      if (processed === null) return;
      data = processed;
    }

    // OSC escape handling
    const afterOsc = processOscEscapes(data, oscHandlers);
    if (afterOsc) {
      writeBuf += afterOsc;
      if (!writeRaf) {
        writeRaf = requestAnimationFrame(() => {
          if (writeBuf) inst.terminal.write(writeBuf);
          writeBuf = "";
          writeRaf = 0;
        });
      }
    }
  };

  inst.ws.onerror = () => {
    adapter.onStatusChange?.("error");
    console.warn("[TerminalFactory] WebSocket error");
  };

  inst.ws.onclose = () => {
    inst.connected = false;
    adapter.onStatusChange?.("disconnected");
    console.log(
      `[TerminalFactory] Disconnected, reconnecting in ${reconnectDelay}ms`,
    );
    setTimeout(
      () => connectInstance(inst, adapter, oscHandlers, reconnectDelay),
      reconnectDelay,
    );
  };
}

/* ── Instance utilities ─────────────────────────────── */

export function fitInstance(inst: TerminalInstance): void {
  if (inst.fitAddon) {
    try {
      inst.fitAddon.fit();
      sendResize(inst);
    } catch {
      /* container may be hidden */
    }
  }
}

export function destroyInstance(inst: TerminalInstance): void {
  inst.resizeObserver?.disconnect();
  if (inst.resizeTimeout) clearTimeout(inst.resizeTimeout);
  inst.ws?.close();
  inst.terminal?.dispose();
}

/* ── Optional features (clipboard, drag-drop) ──────── */

export function setupClipboardHandler(inst: TerminalInstance): void {
  inst.terminal.attachCustomKeyEventHandler((ev: KeyboardEvent) => {
    // Ctrl+C: copy selection if text is selected, else pass through as SIGINT
    if (ev.ctrlKey && (ev.key === "c" || ev.key === "C")) {
      const sel = inst.terminal.getSelection();
      if (sel) {
        navigator.clipboard.writeText(sel);
        return false;
      }
      return true;
    }
    // Ctrl+V: paste from clipboard
    if (ev.ctrlKey && (ev.key === "v" || ev.key === "V")) {
      navigator.clipboard.readText().then((t: string) => {
        if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send(t);
      });
      return false;
    }
    return true;
  });
}

export function setupDragDrop(
  container: HTMLElement,
  inst: TerminalInstance,
  onFileDrop?: (files: FileList) => Promise<string[]>,
): void {
  container.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    container.classList.add("stx-shell-drop-target");
  });
  container.addEventListener("dragleave", () => {
    container.classList.remove("stx-shell-drop-target");
  });
  container.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    container.classList.remove("stx-shell-drop-target");
    const dt = e.dataTransfer;
    if (!dt) return;

    if (dt.files && dt.files.length > 0 && onFileDrop) {
      void (async () => {
        try {
          const paths = await onFileDrop(dt.files);
          if (inst.ws?.readyState === WebSocket.OPEN) {
            inst.ws.send(paths.join(" "));
          }
        } catch (err) {
          console.error("[TerminalFactory] File drop error:", err);
        }
      })();
      return;
    }

    // Text drop (file paths separated by semicolons)
    const raw = dt.getData("text/plain") ?? "";
    const paths = raw.split(";").filter(Boolean);
    if (paths.length > 0 && inst.ws?.readyState === WebSocket.OPEN) {
      inst.ws.send(paths.join(" "));
    }
  });
}

/* ── High-level init function ───────────────────────── */

const DEFAULT_CONTAINER = "#stx-shell-ai-console-terminal";

export async function initTerminal(
  config: TerminalConfig,
): Promise<TerminalInstance | null> {
  const containerEl =
    typeof config.container === "string"
      ? document.getElementById(
          (config.container || DEFAULT_CONTAINER).replace("#", ""),
        )
      : config.container;

  if (!containerEl) {
    console.log("[TerminalFactory] No terminal container found, skipping");
    return null;
  }

  loadXtermCSS();
  const { Terminal, FitAddon } = await loadXtermModules();
  if (!Terminal) {
    console.error("[TerminalFactory] Failed to load xterm.js");
    return null;
  }

  const inst = createTerminalInstance(containerEl, Terminal, FitAddon);

  // Clipboard handler (on by default)
  if (config.clipboard !== false) {
    setupClipboardHandler(inst);
  }

  // Drag-drop (off by default, needs upload handler)
  if (config.dragDrop && config.onFileDrop) {
    setupDragDrop(containerEl, inst, config.onFileDrop);
  }

  // OSC handlers
  const oscHandlers = createDefaultOscHandlers(inst);

  // Connect
  connectInstance(
    inst,
    config.adapter,
    oscHandlers,
    config.reconnectDelay ?? 3000,
  );

  console.log("[TerminalFactory] Initialized");
  return inst;
}
