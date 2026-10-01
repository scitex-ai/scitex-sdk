/* AUTO-GENERATED from ts/app/attachment/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/attachment/index.ts --bundle --format=esm --outfile=js/app/attachment.js */

// ts/app/attachment/_attachment.ts
var PAPERCLIP_PREFIX = "\u{1F4CE} ";
function renderImageAttachment(config) {
  const link = document.createElement("a");
  link.className = "stx-app-attachment stx-app-attachment--image";
  link.href = config.href;
  link.target = "_blank";
  link.rel = "noopener";
  const img = document.createElement("img");
  img.src = config.src ?? config.href;
  img.alt = config.alt;
  img.loading = "lazy";
  link.appendChild(img);
  return link;
}
function renderFileAttachment(config) {
  const link = document.createElement("a");
  link.className = "stx-app-attachment stx-app-attachment--file";
  link.href = config.href;
  link.target = "_blank";
  link.rel = "noopener";
  if (config.iconClass) {
    const icon = document.createElement("i");
    icon.className = config.iconClass;
    link.append(icon, ` ${config.name}`);
  } else {
    link.textContent = `${PAPERCLIP_PREFIX}${config.name}`;
  }
  return link;
}
export {
  renderFileAttachment,
  renderImageAttachment
};
