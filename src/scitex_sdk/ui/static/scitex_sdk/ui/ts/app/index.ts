/**
 * App components — reusable feature UI (file browser, docs sidebar).
 */
export { renderImageAttachment, renderFileAttachment } from "./attachment";
export type { ImageAttachmentConfig, FileAttachmentConfig } from "./attachment";

export { renderEmptyState } from "./empty";
export type { EmptyStateConfig } from "./empty";

export { FileBrowser } from "./file-browser";
export type { FileNode, FileBrowserConfig } from "./file-browser";

export { PackageDocsSidebar } from "./package-docs-sidebar";
export type {
  PackageInfo,
  PackageDocsSidebarConfig,
} from "./package-docs-sidebar";

export { ContextMenu, initContextMenu } from "./context-menu";
export type {
  ContextMenuConfig,
  ContextMenuEntry,
  ContextMenuItem,
  ContextMenuDivider,
  ContextMenuLabel,
} from "./context-menu";

export { Receipt, renderReceipt, RECEIPT_STATES } from "./receipt";
export type {
  ReceiptConfig,
  ReceiptGlyphs,
  ReceiptLabels,
  ReceiptState,
} from "./receipt";

export { ReplyQuote, renderReplyQuote } from "./reply-quote";
export type { ReplyQuoteConfig } from "./reply-quote";

export {
  applyVerdict,
  ALLOWED,
  DENIED,
  DENIED_NOT_SIGNED_IN,
  DENIED_NOT_ENTITLED,
} from "./dim";
export type {
  AllowedVerdict,
  DeniedVerdict,
  DeniedNotSignedInVerdict,
  DeniedNotEntitledVerdict,
  DimConfig,
  DimLabels,
  Verdict,
  VerdictKind,
} from "./dim";

export { AppLauncher, APP_LAUNCHER_SELECT } from "./app-launcher";
export type {
  AppLauncherConfig,
  AppOption,
  AppLauncherSelectDetail,
} from "./app-launcher";

export {
  Panes,
  PANES_CHANGE,
  mountPanes,
  getPanes,
  showPane,
  stxPanes,
} from "./panes";
export type { PaneInfo, PanesChangeDetail, PanesOptions } from "./panes";

export { ImportExport, IMPORT_EXPORT_CONFIRM } from "./import-export";
export type {
  ImportExportConfig,
  FormatOption,
  ImportExportDetail,
} from "./import-export";

export {
  ProjectSelector,
  PROJECT_SELECTOR_CHANGE,
  fuzzyFilter,
  fuzzyScore,
  httpProjectProvider,
  staticProjectProvider,
  mountProjectPickers,
} from "./project-selector";
export type {
  ProjectSelectorConfig,
  ProjectOption,
  ProjectListing,
  ProjectProvider,
} from "./project-selector";
