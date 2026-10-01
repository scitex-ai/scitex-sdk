/**
 * Context-Aware Zoom
 *
 * Tracks which pane the mouse cursor is over and intercepts
 * Ctrl+Wheel / Ctrl++/-/0 to apply zone-specific zoom
 * (font size or scale) instead of browser-wide zoom.
 */

export interface ZoomZone {
  el: HTMLElement;
  getSize: () => number;
  setSize: (val: number) => void;
  min: number;
  max: number;
  default: number;
  storageKey: string;
  /** Step per scroll tick (default 1 for px, 0.05 for CSS zoom) */
  step?: number;
  /** If true, zone handles zoom internally — just preventDefault */
  passthrough?: boolean;
  /** Group name — zones in the same group synchronize their zoom level */
  group?: string;
}

const zones: ZoomZone[] = [];
let activeZone: ZoomZone | null = null;

/** Get the currently active zoom zone (mouse is over it). */
export function getActiveZone(): ZoomZone | null {
  return activeZone;
}

/**
 * Register a DOM element as a zoom zone.
 * When the cursor is over this element, Ctrl+Wheel and Ctrl++/-/0
 * adjust its font size (or delegate to internal handler for passthrough zones).
 */
export function registerZoomZone(zone: ZoomZone): void {
  zones.push(zone);

  // Restore saved size
  const saved = localStorage.getItem(zone.storageKey);
  if (saved) {
    const size = parseFloat(saved);
    console.debug(
      `[zoom] restoring ${zone.storageKey}: saved=${saved}, parsed=${size}, range=[${zone.min},${zone.max}], valid=${size >= zone.min && size <= zone.max}`,
    );
    if (size >= zone.min && size <= zone.max) {
      zone.setSize(size);
    }
  } else {
    console.debug(
      `[zoom] no saved value for ${zone.storageKey}, using default=${zone.default}`,
    );
  }

  zone.el.addEventListener("mouseenter", () => {
    activeZone = zone;
  });
  zone.el.addEventListener("mouseleave", () => {
    if (activeZone !== zone) return;
    // Fall back to the most-specific ancestor zone (fixes nested zone nesting)
    activeZone = null;
    for (const z of zones) {
      if (z !== zone && z.el.contains(zone.el)) {
        if (!activeZone || activeZone.el.contains(z.el)) {
          activeZone = z;
        }
      }
    }
  });
}

function adjustZoom(zone: ZoomZone, direction: number): void {
  if (zone.passthrough) return;
  const step = zone.step ?? 1;
  const current = zone.getSize();
  const raw = current + direction * step;
  // Round to avoid float drift (e.g. 1.0500000000000003)
  const next = Math.min(
    zone.max,
    Math.max(zone.min, Math.round(raw * 1000) / 1000),
  );
  zone.setSize(next);
  localStorage.setItem(zone.storageKey, String(next));
  syncGroup(zone, next);
}

function resetZoom(zone: ZoomZone): void {
  if (zone.passthrough) return;
  zone.setSize(zone.default);
  localStorage.setItem(zone.storageKey, String(zone.default));
  syncGroup(zone, zone.default);
}

/** Propagate zoom level to all other zones in the same group. */
function syncGroup(source: ZoomZone, value: number): void {
  if (!source.group) return;
  for (const z of zones) {
    if (z === source || z.group !== source.group || z.passthrough) continue;
    const clamped = Math.min(z.max, Math.max(z.min, value));
    z.setSize(clamped);
    localStorage.setItem(z.storageKey, String(clamped));
  }
}

/**
 * Initialize global event listeners for context-aware zoom.
 * Call once at app startup.
 */
let contextZoomInited = false;
export function initContextZoom(): void {
  if (contextZoomInited) return;
  contextZoomInited = true;
  // Ctrl+Wheel — zoom the zone under the cursor
  document.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey) return;
      if (!activeZone) return;
      e.preventDefault();
      if (activeZone.passthrough) return;
      const delta = e.deltaY < 0 ? 1 : -1;
      adjustZoom(activeZone, delta);
    },
    { passive: false },
  );

  // Ctrl++/-/0 — zoom the zone under the cursor
  document.addEventListener("keydown", (e) => {
    if (!e.ctrlKey || e.altKey || !activeZone) return;

    if (e.key === "=" || e.key === "+") {
      e.preventDefault();
      adjustZoom(activeZone, 1);
      return;
    }
    if (e.key === "-") {
      e.preventDefault();
      adjustZoom(activeZone, -1);
      return;
    }
    if (e.key === "0") {
      e.preventDefault();
      resetZoom(activeZone);
    }
  });
}

/**
 * Convenience: register a CSS-zoom zone by selector.
 * Uses the `zoom` property so ALL content (text, padding, borders) scales uniformly,
 * even when child elements have explicit px font sizes.
 * Returns true if the element was found and registered.
 */
export function registerFontZoom(
  selector: string,
  storageKey: string,
  _defaultSize = 13,
  opts?: {
    passthrough?: boolean;
    min?: number;
    max?: number;
    /** Group name — zones in the same group synchronize their zoom level */
    group?: string;
  },
): boolean {
  const el = document.querySelector<HTMLElement>(selector);
  if (!el) return false;
  registerZoomZone({
    el,
    getSize: () => parseFloat(el.style.zoom || "1"),
    setSize: (val) => {
      el.style.zoom = String(val);
    },
    min: opts?.min ?? 0.6,
    max: opts?.max ?? 2.0,
    default: 1.0,
    step: 0.05,
    storageKey,
    passthrough: opts?.passthrough,
    group: opts?.group,
  });
  return true;
}

/**
 * Register a font-size zoom zone.
 *
 * Adjusts `font-size` (in px) on targeted elements within the zone container.
 * Unlike `registerFontZoom` (CSS zoom), this only scales text — padding, borders,
 * and layout stay fixed. Ideal for file lists, code views, and plugin panels.
 *
 * @param selector  CSS selector for the zone container (mouse-tracking area)
 * @param storageKey  localStorage key for persistence
 * @param opts.target  CSS selector for elements to apply font-size to.
 *                     If omitted, applies to the zone element itself.
 * @param opts.group   Group name — zones in the same group synchronize.
 */
export function registerFontSizeZoom(
  selector: string,
  storageKey: string,
  opts?: {
    defaultSize?: number;
    min?: number;
    max?: number;
    step?: number;
    group?: string;
    /** CSS selector for target elements within the zone. Omit = zone element. */
    target?: string;
  },
): boolean {
  const el = document.querySelector<HTMLElement>(selector);
  if (!el) return false;
  const zoneEl: HTMLElement = el;

  const defaultSize = opts?.defaultSize ?? 13;
  const targetSel = opts?.target;

  function getTargets(): HTMLElement[] {
    if (!targetSel) return [zoneEl];
    return Array.from(zoneEl.querySelectorAll<HTMLElement>(targetSel));
  }

  registerZoomZone({
    el,
    getSize: () => {
      const targets = getTargets();
      if (targets.length === 0) return defaultSize;
      return parseFloat(targets[0].style.fontSize || String(defaultSize));
    },
    setSize: (val) => {
      const px = `${val}px`;
      for (const t of getTargets()) {
        t.style.fontSize = px;
      }
    },
    min: opts?.min ?? 8,
    max: opts?.max ?? 24,
    default: defaultSize,
    step: opts?.step ?? 1,
    storageKey,
    group: opts?.group,
  });
  return true;
}

// ── Zoom indicator ──────────────────────────────────────────────────
let indicatorEl: HTMLElement | null = null;
let indicatorTimer = 0;

function showZoomIndicator(pct: string, x: number, y: number): void {
  if (!indicatorEl) {
    indicatorEl = document.createElement("div");
    Object.assign(indicatorEl.style, {
      position: "fixed",
      padding: "2px 8px",
      borderRadius: "4px",
      background: "rgba(0,0,0,0.7)",
      color: "#fff",
      fontSize: "12px",
      fontFamily: "monospace",
      pointerEvents: "none",
      zIndex: "99999",
      opacity: "0",
      transition: "opacity 0.15s",
    });
    document.body.appendChild(indicatorEl);
  }
  indicatorEl.textContent = pct;
  indicatorEl.style.left = `${x}px`;
  indicatorEl.style.top = `${y}px`;
  indicatorEl.style.opacity = "1";
  clearTimeout(indicatorTimer);
  indicatorTimer = window.setTimeout(() => {
    if (indicatorEl) indicatorEl.style.opacity = "0";
  }, 800);
}

function getZoomLabel(): string | null {
  const zone = getActiveZone();
  if (!zone || zone.passthrough) return null;
  const val = zone.getSize();
  if (zone.step && zone.step < 1) return `${Math.round(val * 100)}%`;
  return `${Math.round(val)}px`;
}

let indicatorAttached = false;
function attachZoomIndicator(): void {
  if (indicatorAttached) return;
  indicatorAttached = true;
  let mx = 0,
    my = 0;
  document.addEventListener("mousemove", (e) => {
    mx = e.clientX;
    my = e.clientY;
  });
  const show = () =>
    requestAnimationFrame(() => {
      const label = getZoomLabel();
      if (label) showZoomIndicator(label, mx + 16, my - 24);
    });
  document.addEventListener(
    "wheel",
    (e) => {
      if (e.ctrlKey) show();
    },
    { passive: true },
  );
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && !e.altKey && "=+-0".includes(e.key)) show();
  });
}

// ── Declarative zone registration with MutationObserver ─────────────

export interface FontZoomDef {
  selector: string;
  storageKey: string;
  min?: number;
  max?: number;
  group?: string;
  passthrough?: boolean;
}

export interface FontSizeZoomDef {
  selector: string;
  storageKey: string;
  defaultSize?: number;
  min?: number;
  max?: number;
  step?: number;
  group?: string;
  target?: string;
}

/**
 * Initialize context zoom and register zones declaratively.
 *
 * Uses MutationObserver to wait for elements that may not exist yet
 * (e.g. React-rendered panes). Safe to call once at app startup.
 *
 * @param fontZoomZones   Array of CSS-zoom zone definitions
 * @param fontSizeZoomZones  Array of font-size zoom zone definitions
 * @param timeoutMs       Stop observing after this many ms (default 30s)
 */
export function bootstrapContextZoom(
  fontZoomZones: FontZoomDef[] = [],
  fontSizeZoomZones: FontSizeZoomDef[] = [],
  timeoutMs = 30_000,
): void {
  // initContextZoom and attachZoomIndicator are idempotent
  initContextZoom();
  attachZoomIndicator();

  const registered = new Set<string>();
  const totalExpected = fontZoomZones.length + fontSizeZoomZones.length;

  function registerPending(): number {
    let count = 0;
    for (const z of fontZoomZones) {
      if (registered.has(z.selector)) continue;
      const found = !!document.querySelector(z.selector);
      if (found && registerFontZoom(z.selector, z.storageKey, 1, z)) {
        registered.add(z.selector);
        count++;
        console.log("[zoom] CSS-zoom registered:", z.selector);
      }
    }
    for (const z of fontSizeZoomZones) {
      if (registered.has(z.selector)) continue;
      const found = !!document.querySelector(z.selector);
      if (found && registerFontSizeZoom(z.selector, z.storageKey, z)) {
        registered.add(z.selector);
        count++;
        console.log("[zoom] font-size registered:", z.selector);
      }
    }
    return count;
  }

  // Try immediately
  const initial = registerPending();
  console.log(
    "[zoom] initial registration:",
    initial,
    "/",
    totalExpected,
    "zones",
  );

  // Watch for lazy-loaded panes
  if (registered.size < totalExpected) {
    console.log(
      "[zoom] starting MutationObserver for remaining",
      totalExpected - registered.size,
      "zones",
    );
    const observer = new MutationObserver(() => {
      const added = registerPending();
      if (added > 0) {
        console.log(
          "[zoom] observer registered",
          added,
          "more zones, total:",
          registered.size,
          "/",
          totalExpected,
        );
      }
      if (registered.size >= totalExpected) {
        observer.disconnect();
        console.log("[zoom] all zones registered, observer disconnected");
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(() => {
      observer.disconnect();
      if (registered.size < totalExpected) {
        console.warn(
          "[zoom] timeout: only",
          registered.size,
          "/",
          totalExpected,
          "zones registered",
        );
      }
    }, timeoutMs);
  }
}
