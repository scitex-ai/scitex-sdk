/* AUTO-GENERATED from ts/app/empty/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/empty/index.ts --bundle --format=esm --outfile=js/app/empty.js */

// ts/app/empty/_EmptyState.ts
function renderEmptyState(config) {
  const el = document.createElement("div");
  el.className = "stx-app-empty";
  if (config.compact) el.classList.add("stx-app-empty--compact");
  el.setAttribute("role", "status");
  if (config.iconClass && !config.compact) {
    const icon = document.createElement("i");
    icon.className = `stx-app-empty__icon ${config.iconClass}`;
    icon.setAttribute("aria-hidden", "true");
    el.appendChild(icon);
  }
  const title = document.createElement("div");
  title.className = "stx-app-empty__title";
  title.textContent = config.title;
  el.appendChild(title);
  if (config.hint) {
    const hint = document.createElement("div");
    hint.className = "stx-app-empty__hint";
    hint.textContent = config.hint;
    el.appendChild(hint);
  }
  if (config.action && !config.compact) {
    const wrap = document.createElement("div");
    wrap.className = "stx-app-empty__action";
    wrap.appendChild(config.action);
    el.appendChild(wrap);
  }
  return el;
}
export {
  renderEmptyState
};
