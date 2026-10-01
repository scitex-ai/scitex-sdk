/**
 * Monaco Loader — scitex-ui
 * Single entry point for Monaco initialization.
 * Imports monaco-editor npm package, sets up workers, registers languages.
 *
 * Side-effect module: importing this file initializes Monaco globally.
 */

import * as monaco from "monaco-editor";
import "monaco-editor/min/vs/editor/editor.main.css";

import { registerCustomLanguages } from "./_MonacoLanguages";

// ── Worker environment (main-thread fallback) ────────────────────────

interface FakeWorker {
  postMessage: () => void;
  terminate: () => void;
  addEventListener: () => void;
  removeEventListener: () => void;
}

function createFakeWorker(): FakeWorker {
  return {
    postMessage: () => {},
    terminate: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
  };
}

(self as any).MonacoEnvironment = {
  getWorker(_moduleId: string, _label: string): FakeWorker {
    return createFakeWorker();
  },
};

// ── Initialize ───────────────────────────────────────────────────────

registerCustomLanguages(monaco);

(window as any).monaco = monaco;
(window as any).monacoReady = true;
(window as any).monacoLoaded = true;
window.dispatchEvent(new Event("monaco-ready"));

// ── Exports ──────────────────────────────────────────────────────────

export { monaco };

/**
 * Wait for Monaco to be available on window.
 * Resolves immediately if already loaded.
 */
export function waitForMonaco(): Promise<typeof monaco> {
  return new Promise((resolve) => {
    if ((window as any).monaco) {
      resolve(monaco);
      return;
    }

    const handler = () => {
      setTimeout(() => resolve(monaco), 50);
    };
    window.addEventListener("monaco-ready", handler, { once: true });

    // Polling fallback
    let attempts = 0;
    const check = () => {
      attempts++;
      if ((window as any).monaco) {
        resolve(monaco);
      } else if (attempts < 100) {
        setTimeout(check, 100);
      } else {
        throw new Error("[MonacoLoader] Monaco failed to load after 10s");
      }
    };
    check();
  });
}
