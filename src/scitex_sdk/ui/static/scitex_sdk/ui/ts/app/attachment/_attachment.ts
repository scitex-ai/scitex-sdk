/**
 * Attachment chips — image and file, harvested from scitex-cards.
 *
 * PRESENTATION ONLY. Base owns no part of the storage path: scitex-cards is
 * moving attachments from an interim body-URL convention into a cards.db
 * table, and encoding either here would bake in a plumbing decision that is
 * theirs and already changing. These take a URL and render it.
 *
 * The markup contract is preserved exactly as they shipped it, because their
 * adoption should be a deletion rather than a visual regression:
 *   - the image anchor WRAPS the img (so the size cap lives on the img)
 *   - the img is `loading="lazy"`
 *   - both anchors are target=_blank rel=noopener
 *   - the file chip's paperclip is a literal text prefix, not a pseudo-element
 */

import type { FileAttachmentConfig, ImageAttachmentConfig } from "./types";

const PAPERCLIP_PREFIX = "📎 ";

/** `<a class="stx-app-attachment stx-app-attachment--image"><img loading="lazy"></a>` */
export function renderImageAttachment(
  config: ImageAttachmentConfig,
): HTMLAnchorElement {
  const link = document.createElement("a");
  link.className = "stx-app-attachment stx-app-attachment--image";
  link.href = config.href;
  link.target = "_blank";
  link.rel = "noopener";

  const img = document.createElement("img");
  img.src = config.src ?? config.href;
  img.alt = config.alt;
  // Attachments sit in a scrolling transcript, so most are off-screen when the
  // message renders. Eager loading would fetch every image in the history.
  img.loading = "lazy";

  link.appendChild(img);
  return link;
}

/** `<a class="stx-app-attachment stx-app-attachment--file">📎 name</a>` */
export function renderFileAttachment(
  config: FileAttachmentConfig,
): HTMLAnchorElement {
  const link = document.createElement("a");
  link.className = "stx-app-attachment stx-app-attachment--file";
  link.href = config.href;
  link.target = "_blank";
  link.rel = "noopener";

  if (config.iconClass) {
    // Opt-in alternative contract — see types.ts.
    const icon = document.createElement("i");
    icon.className = config.iconClass;
    link.append(icon, ` ${config.name}`);
  } else {
    link.textContent = `${PAPERCLIP_PREFIX}${config.name}`;
  }
  return link;
}
