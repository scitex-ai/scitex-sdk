/** Standalone shell initialization.
 *  Loaded by standalone_shell.html after DOM is ready.
 *
 *  Wires:
 *  - Console/Chat mode toggle
 *  - Toolbar buttons (camera, sketch, mic) → custom DOM events
 *  - Config popover gear toggle (direct, like scitex-hub)
 *  - Sidebar header double-click → collapse
 *
 *  Apps listen for these events to implement actual functionality:
 *    window.addEventListener("stx-shell:camera", handler)
 *    window.addEventListener("stx-shell:sketch", handler)
 *    window.addEventListener("stx-shell:mic-toggle", handler)
 *    window.addEventListener("stx-shell:settings", handler)
 */

(function () {
  "use strict";

  /* ── Console/Chat mode toggle ─────────────────────── */
  document.querySelectorAll(".stx-shell-ai-mode-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var mode = btn.dataset.mode;
      document.querySelectorAll(".stx-shell-ai-mode-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      document.querySelectorAll(".stx-shell-ai-view").forEach(function (v) {
        v.classList.remove("active");
      });
      var target = document.getElementById(
        mode === "chat"
          ? "stx-shell-ai-chat-view"
          : "stx-shell-ai-console-view",
      );
      if (target) target.classList.add("active");
    });
  });

  /* ── Config popover gear toggles (console + chat) ──── */
  var gearPairs = [
    {
      btn: document.querySelector(
        "#stx-shell-ai-console-view .stx-shell-ai-gear-btn",
      ),
      popover: document.getElementById("stx-shell-ai-console-config"),
    },
    {
      btn: document.getElementById("stx-shell-ai-chat-gear"),
      popover: document.getElementById("stx-shell-ai-chat-config"),
    },
  ];

  gearPairs.forEach(function (pair) {
    if (!pair.btn || !pair.popover) return;
    var btn = pair.btn;
    var popover = pair.popover;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      // Close all other popovers first
      document
        .querySelectorAll(".stx-shell-ai-config-popover")
        .forEach(function (p) {
          if (p !== popover) p.classList.add("stx-hidden");
        });
      popover.classList.toggle("stx-hidden");
      window.dispatchEvent(new CustomEvent("stx-shell:settings"));
    });
  });

  // Click-outside to close any open popover
  document.addEventListener("mousedown", function (e) {
    document
      .querySelectorAll(".stx-shell-ai-config-popover")
      .forEach(function (p) {
        if (p.classList.contains("stx-hidden")) return;
        var isGear = false;
        gearPairs.forEach(function (pair) {
          if (pair.btn && pair.btn.contains(e.target)) isGear = true;
        });
        if (!p.contains(e.target) && !isGear) {
          p.classList.add("stx-hidden");
        }
      });
  });

  /* ── Toolbar buttons → custom events ──────────────── */
  var toolbarBtns = document.querySelectorAll(".stx-shell-ai-input-btn");
  toolbarBtns.forEach(function (btn) {
    if (btn.disabled) return;
    var title = (btn.getAttribute("title") || "").toLowerCase();
    var eventName = null;

    if (title.indexOf("webcam") >= 0 || title.indexOf("camera") >= 0) {
      eventName = "stx-shell:camera";
    } else if (title.indexOf("sketch") >= 0 || title.indexOf("draw") >= 0) {
      eventName = "stx-shell:sketch";
    } else if (title.indexOf("voice") >= 0 || title.indexOf("mic") >= 0) {
      eventName = "stx-shell:mic-toggle";
    }
    // Settings/config handled by gear toggle above — skip

    if (eventName) {
      btn.addEventListener("click", function () {
        window.dispatchEvent(new CustomEvent(eventName));
      });
    }
  });

  /* ── Keyboard shortcuts button → toggle modal ────────── */
  var shortcutsBtn = document.getElementById("stx-shell-shortcuts-btn");
  if (shortcutsBtn) {
    shortcutsBtn.addEventListener("click", function () {
      if (typeof window.toggleShortcutsModal === "function") {
        window.toggleShortcutsModal();
      }
    });
  }

  /* ── Readiness fallback for bare shell pages ──────────
   * The shared workspace-panel-resizer module marks containers panels-ready
   * and drops the body.no-transition visibility guard when an app bundle
   * loads it. Pages served with only the shell scripts never get that call,
   * so their panes stay hidden and the body keeps the guard. After load, if
   * containers exist but none is marked, apply the same two DOM operations.
   * The marked check runs again at mutation time inside the animation frames:
   * a module that marks between scheduling and paint still wins, so this
   * never overrides the shared initializer. No-op when no containers exist. */
  function markReadyFallback() {
    var containers = document.querySelectorAll(
      ".workspace-three-col, .workspace-shell",
    );
    if (!containers.length) return;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var marked = document.querySelectorAll(
          ".workspace-three-col.panels-ready, .workspace-shell.panels-ready",
        );
        if (marked.length) return;
        containers.forEach(function (el) {
          el.classList.add("panels-ready");
        });
        document.body.classList.remove("no-transition");
      });
    });
  }
  if (document.readyState === "complete") {
    markReadyFallback();
  } else {
    window.addEventListener("load", markReadyFallback);
  }
})();
