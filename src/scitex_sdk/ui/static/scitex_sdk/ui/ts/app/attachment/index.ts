/**
 * Attachment chips — inline image and file-link presentation.
 *
 *   import { renderImageAttachment, renderFileAttachment }
 *     from "scitex-ui/ts/app/attachment";
 *
 *   msg.appendChild(renderImageAttachment({ href: url, alt: "screenshot" }));
 *   msg.appendChild(renderFileAttachment({ href: url, name: "report.pdf" }));
 *
 * Presentation only — base owns no storage path. Styling:
 * `css/app/attachment.css`, paired with `css/shell/theme.css` for the tokens.
 */

export { renderImageAttachment, renderFileAttachment } from "./_attachment";
export type { ImageAttachmentConfig, FileAttachmentConfig } from "./types";

export { attachmentKind } from "./_kind";
export type { AttachmentKind } from "./_kind";
