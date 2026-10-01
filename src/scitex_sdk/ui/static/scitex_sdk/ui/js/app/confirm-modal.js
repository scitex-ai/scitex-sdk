/* AUTO-GENERATED from ts/app/confirm-modal/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/confirm-modal/index.ts --bundle --format=esm --outfile=js/app/confirm-modal.js */

// ts/app/confirm-modal/_showConfirm.ts
var CLS = "stx-app-confirm-modal";
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
function showConfirm(options) {
  const {
    title = "Confirm",
    message,
    confirmText = "Confirm",
    cancelText = "Cancel",
    onConfirm,
    onCancel
  } = options;
  document.getElementById(`${CLS}-overlay`)?.remove();
  const overlay = document.createElement("div");
  overlay.id = `${CLS}-overlay`;
  overlay.className = `${CLS}__overlay`;
  overlay.innerHTML = `
    <div class="${CLS}__content">
      <div class="${CLS}__header">
        <h3>${escapeHtml(title)}</h3>
        <button class="${CLS}__close" aria-label="Close">&times;</button>
      </div>
      <div class="${CLS}__body">
        <p>${escapeHtml(message)}</p>
      </div>
      <div class="${CLS}__footer">
        <button class="${CLS}__btn ${CLS}__btn--cancel" data-action="cancel">${escapeHtml(cancelText)}</button>
        <button class="${CLS}__btn ${CLS}__btn--confirm" data-action="confirm">${escapeHtml(confirmText)}</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  const close = () => {
    overlay.classList.add(`${CLS}__overlay--closing`);
    setTimeout(() => overlay.remove(), 200);
  };
  overlay.querySelector(`.${CLS}__close`)?.addEventListener("click", () => {
    onCancel?.();
    close();
  });
  overlay.querySelector('[data-action="cancel"]')?.addEventListener("click", () => {
    onCancel?.();
    close();
  });
  overlay.querySelector('[data-action="confirm"]')?.addEventListener("click", () => {
    onConfirm?.();
    close();
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      onCancel?.();
      close();
    }
  });
  const escHandler = (e) => {
    if (e.key === "Escape") {
      onCancel?.();
      close();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);
  setTimeout(() => overlay.classList.add(`${CLS}__overlay--visible`), 10);
  overlay.querySelector('[data-action="confirm"]')?.focus();
}
export {
  showConfirm
};
