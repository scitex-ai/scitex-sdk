/* AUTO-GENERATED from ts/app/reply-quote/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/reply-quote/index.ts --bundle --format=esm --outfile=js/app/reply-quote.js */
var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// ts/app/reply-quote/_ReplyQuote.ts
var FLASH_MS_DEFAULT = 1200;
var FLASH_CLASS = "stx-app-reply-quote-target--flash";
var ReplyQuote = class {
  constructor(config) {
    __publicField(this, "el");
    __publicField(this, "config");
    this.config = config;
    this.el = document.createElement("button");
    this.el.type = "button";
    this.el.className = "stx-app-reply-quote";
    const author = document.createElement("span");
    author.className = "stx-app-reply-quote__author";
    author.textContent = config.author;
    const text = document.createElement("span");
    text.className = "stx-app-reply-quote__text";
    text.textContent = config.text;
    this.el.append(author, text);
    this.el.setAttribute(
      "aria-label",
      `Reply to ${config.author}: ${config.text}`
    );
    this.el.addEventListener("click", () => this.activate());
    if (!config.onActivate && !this.resolveTarget()) this.markOrphaned();
  }
  /** Jump to the original. Returns false when it could not be reached. */
  activate() {
    if (this.config.onActivate) {
      const handled = this.config.onActivate(this.config.targetId);
      if (!handled) this.markOrphaned();
      return handled;
    }
    const target = this.resolveTarget();
    if (!target) {
      this.markOrphaned();
      return false;
    }
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add(FLASH_CLASS);
    window.setTimeout(
      () => target.classList.remove(FLASH_CLASS),
      this.config.flashMs ?? FLASH_MS_DEFAULT
    );
    return true;
  }
  /** Whether this quote currently believes it can reach its original. */
  get orphaned() {
    return this.el.classList.contains("stx-app-reply-quote--orphaned");
  }
  resolveTarget() {
    const id = this.config.targetId;
    if (!id) return null;
    return document.getElementById(id);
  }
  markOrphaned() {
    this.el.classList.add("stx-app-reply-quote--orphaned");
    this.el.disabled = true;
    this.el.title = "The original message is no longer available";
  }
};
function renderReplyQuote(config) {
  return new ReplyQuote(config);
}
export {
  ReplyQuote,
  renderReplyQuote
};
