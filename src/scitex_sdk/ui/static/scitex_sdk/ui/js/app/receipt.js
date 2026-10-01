/* AUTO-GENERATED from ts/app/receipt/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/receipt/index.ts --bundle --format=esm --outfile=js/app/receipt.js */
var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// ts/app/receipt/types.ts
var RECEIPT_STATES = [
  "unknown",
  "sent",
  "seen",
  "failed"
];

// ts/app/receipt/_Receipt.ts
var DEFAULT_GLYPHS = {
  unknown: "\xB7",
  sent: "\u26A1",
  seen: "\u{1F440}",
  failed: "\u26A0"
};
var DEFAULT_LABELS = {
  unknown: "Delivery status unknown",
  sent: "Delivered to the store",
  seen: "Seen by the recipient",
  failed: "Delivery failed"
};
var Receipt = class {
  constructor(config = {}) {
    __publicField(this, "el");
    __publicField(this, "current");
    __publicField(this, "glyphs");
    __publicField(this, "labels");
    this.glyphs = { ...DEFAULT_GLYPHS, ...config.glyphs };
    this.labels = { ...DEFAULT_LABELS, ...config.labels };
    this.current = config.state ?? "unknown";
    assertState(this.current);
    this.el = document.createElement("span");
    this.el.className = "stx-app-receipt";
    this.el.setAttribute("role", "img");
    this.paint();
  }
  /** The state as last set. Never inferred, never guessed. */
  get state() {
    return this.current;
  }
  /**
   * Move to a state. Throws on anything outside the four — an unrecognised
   * status must fail loudly here rather than silently render as `unknown`,
   * which would be indistinguishable from "no signal yet".
   */
  set(state) {
    assertState(state);
    this.current = state;
    this.paint();
  }
  paint() {
    for (const s of RECEIPT_STATES) {
      this.el.classList.toggle(`stx-app-receipt--${s}`, s === this.current);
    }
    this.el.textContent = this.glyphs[this.current];
    this.el.title = this.labels[this.current];
    this.el.setAttribute("aria-label", this.labels[this.current]);
    this.el.dataset.state = this.current;
  }
};
function assertState(state) {
  if (!RECEIPT_STATES.includes(state)) {
    throw new Error(
      `[receipt] unknown state ${JSON.stringify(state)}; expected one of ${RECEIPT_STATES.join(", ")}. Rendering it as "unknown" would hide a delivery failure behind a state that means "no signal yet".`
    );
  }
}
function renderReceipt(config = {}) {
  return new Receipt(config);
}
export {
  RECEIPT_STATES,
  Receipt,
  renderReceipt
};
