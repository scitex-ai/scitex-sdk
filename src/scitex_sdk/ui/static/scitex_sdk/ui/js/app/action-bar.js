/* AUTO-GENERATED from ts/app/action-bar/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/action-bar/auto-mount.ts --bundle --format=esm --outfile=js/app/action-bar.js */

// .worktrees/action-bar/src/scitex_ui/static/scitex_ui/ts/app/action-bar/types.ts
var ACTION_BAR_CHANGE = "stx-action-bar:change";

// .worktrees/action-bar/src/scitex_ui/static/scitex_ui/ts/app/action-bar/_ActionBar.ts
var BAR_ATTRIBUTE = "data-stx-action-bar";
var ITEM_ATTRIBUTE = "data-stx-action-bar-item";
var MOUNTED_ATTRIBUTE = "data-stx-action-bar-mounted";
var HEIGHT_PROPERTY = "--stx-action-bar-height";
var CLS = "stx-action-bar";
var CLS_ITEM = `${CLS}__item`;
var ActionBar = class {
  element;
  reserveOn;
  shouldMeasure;
  observer = null;
  lastHeight = 0;
  constructor(element, options = {}) {
    this.element = element;
    this.shouldMeasure = options.measure !== false;
    this.reserveOn = options.reserveOn === void 0 ? element.parentElement : options.reserveOn;
    element.classList.add(CLS);
    for (const item of Array.from(
      element.querySelectorAll(`[${ITEM_ATTRIBUTE}]`)
    )) {
      item.classList.add(CLS_ITEM);
    }
    this.refresh();
    this.observe();
  }
  /** The last measured height in CSS pixels (0 before the first measurement). */
  get height() {
    return this.lastHeight;
  }
  /** Re-measure now and republish. Safe to call any number of times. */
  refresh() {
    const height = this.shouldMeasure ? Math.round(this.element.getBoundingClientRect().height) : this.lastHeight;
    this.publish(height);
    return height;
  }
  /** Stop observing. The classes and the published height are left in place. */
  destroy() {
    this.observer?.disconnect();
    this.observer = null;
  }
  observe() {
    if (!this.shouldMeasure || typeof ResizeObserver === "undefined") return;
    this.observer = new ResizeObserver(() => {
      this.refresh();
    });
    this.observer.observe(this.element);
  }
  publish(height) {
    if (height === this.lastHeight) return;
    this.lastHeight = height;
    this.reserveOn?.style.setProperty(HEIGHT_PROPERTY, `${height}px`);
    const detail = { height, reserveOn: this.reserveOn };
    this.element.dispatchEvent(
      new CustomEvent(ACTION_BAR_CHANGE, { detail })
    );
  }
};

// .worktrees/action-bar/src/scitex_ui/static/scitex_ui/ts/app/action-bar/mount.ts
var instances = [];
function mountActionBar(root = document, options = {}) {
  const mounted = [];
  for (const element of Array.from(
    root.querySelectorAll(`[${BAR_ATTRIBUTE}]`)
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const bar = new ActionBar(element, options);
    instances.push(bar);
    mounted.push(bar);
  }
  return mounted;
}
function getActionBar() {
  return instances.length > 0 ? instances[instances.length - 1] : null;
}
function actionBarHeight() {
  return getActionBar()?.height ?? 0;
}
var stxActionBar = {
  mount: mountActionBar,
  get: getActionBar,
  height: actionBarHeight
};

// .worktrees/action-bar/src/scitex_ui/static/scitex_ui/ts/app/action-bar/auto-mount.ts
window.stxActionBar = stxActionBar;
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountActionBar());
} else {
  mountActionBar();
}
export {
  ACTION_BAR_CHANGE,
  ActionBar,
  BAR_ATTRIBUTE,
  HEIGHT_PROPERTY,
  ITEM_ATTRIBUTE,
  MOUNTED_ATTRIBUTE,
  actionBarHeight,
  getActionBar,
  mountActionBar,
  stxActionBar
};
