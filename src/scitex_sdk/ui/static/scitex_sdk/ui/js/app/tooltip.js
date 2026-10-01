/* AUTO-GENERATED from ts/app/tooltip/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/tooltip/index.ts --bundle --format=esm --outfile=js/app/tooltip.js */

// ts/_base/aria-describedby.ts
var ATTR = "aria-describedby";
function ids(el) {
  const raw = el.getAttribute(ATTR);
  return raw ? raw.split(/\s+/).filter(Boolean) : [];
}
function write(el, list) {
  if (list.length === 0) {
    el.removeAttribute(ATTR);
    return;
  }
  el.setAttribute(ATTR, list.join(" "));
}
function addDescribedBy(el, id, position = "last") {
  const list = ids(el);
  if (list.includes(id)) return;
  write(el, position === "first" ? [id, ...list] : [...list, id]);
}
function removeDescribedBy(el, id) {
  const list = ids(el);
  if (!list.includes(id)) return;
  write(
    el,
    list.filter((each) => each !== id)
  );
}

// ts/app/tooltip/_Tooltip.ts
var CLS = "stx-app-tooltip";
var MARGIN = 8;
var TOOLTIP_ID = "stx-app-tooltip-description";
var tooltipEl = null;
var showTimeout = null;
var currentTarget = null;
function getOrCreateTooltip() {
  if (!tooltipEl) {
    tooltipEl = document.createElement("div");
    tooltipEl.className = CLS;
    tooltipEl.id = TOOLTIP_ID;
    tooltipEl.setAttribute("role", "tooltip");
    document.body.appendChild(tooltipEl);
  }
  return tooltipEl;
}
function bestPosition(target, preferred) {
  if (preferred !== "auto") return preferred;
  const spaceAbove = target.top;
  const spaceBelow = window.innerHeight - target.bottom;
  const spaceLeft = target.left;
  const spaceRight = window.innerWidth - target.right;
  if (spaceBelow >= 40) return "bottom";
  if (spaceAbove >= 40) return "top";
  if (spaceRight >= 100) return "right";
  if (spaceLeft >= 100) return "left";
  return "bottom";
}
function positionTooltip(tip, target, pos) {
  const tipRect = tip.getBoundingClientRect();
  let top = 0;
  let left = 0;
  switch (pos) {
    case "bottom":
      top = target.bottom + MARGIN;
      left = target.left + target.width / 2 - tipRect.width / 2;
      break;
    case "top":
      top = target.top - tipRect.height - MARGIN;
      left = target.left + target.width / 2 - tipRect.width / 2;
      break;
    case "right":
      top = target.top + target.height / 2 - tipRect.height / 2;
      left = target.right + MARGIN;
      break;
    case "left":
      top = target.top + target.height / 2 - tipRect.height / 2;
      left = target.left - tipRect.width - MARGIN;
      break;
  }
  left = Math.max(4, Math.min(left, window.innerWidth - tipRect.width - 4));
  top = Math.max(4, Math.min(top, window.innerHeight - tipRect.height - 4));
  tip.style.top = `${top + window.scrollY}px`;
  tip.style.left = `${left + window.scrollX}px`;
}
function showTooltip(target, config) {
  const text = target.getAttribute("data-tooltip");
  if (!text) return;
  const tip = getOrCreateTooltip();
  tip.textContent = text;
  tip.style.display = "block";
  tip.style.opacity = "0";
  currentTarget = target;
  addDescribedBy(target, TOOLTIP_ID, "last");
  requestAnimationFrame(() => {
    const rect = target.getBoundingClientRect();
    const preferred = target.getAttribute("data-tooltip-position") || config.position || "auto";
    const pos = bestPosition(rect, preferred);
    positionTooltip(tip, rect, pos);
    tip.dataset.position = pos;
    tip.style.opacity = "1";
  });
}
function hideTooltip() {
  if (showTimeout) {
    clearTimeout(showTimeout);
    showTimeout = null;
  }
  if (currentTarget) {
    removeDescribedBy(currentTarget, TOOLTIP_ID);
  }
  if (tooltipEl) {
    tooltipEl.style.display = "none";
    tooltipEl.style.opacity = "0";
  }
  currentTarget = null;
}
var Tooltip = {
  /** Initialize tooltip system. Call once. */
  init(config = {}) {
    const delay = config.delay ?? 300;
    const root = config.root || document.body;
    root.addEventListener(
      "mouseenter",
      (e) => {
        const target = e.target?.closest?.(
          config.selector || "[data-tooltip]"
        );
        if (!target) return;
        showTimeout = setTimeout(() => showTooltip(target, config), delay);
      },
      true
    );
    root.addEventListener(
      "mouseleave",
      (e) => {
        const target = e.target?.closest?.(
          config.selector || "[data-tooltip]"
        );
        if (target) hideTooltip();
      },
      true
    );
    root.addEventListener(
      "focusin",
      (e) => {
        const target = e.target?.closest?.(
          config.selector || "[data-tooltip]"
        );
        if (target) showTooltip(target, config);
      },
      true
    );
    root.addEventListener(
      "focusout",
      (e) => {
        const target = e.target?.closest?.(
          config.selector || "[data-tooltip]"
        );
        if (target) hideTooltip();
      },
      true
    );
    window.addEventListener("scroll", hideTooltip, true);
    window.addEventListener("resize", hideTooltip);
  },
  /** Programmatically hide tooltip. */
  hide: hideTooltip
};
export {
  Tooltip
};
