// App components (React)
export { AlertBanner } from "./alert-banner";
export type { AlertBannerProps, AlertBannerType } from "./alert-banner";

export { FileBrowser } from "./file-browser";
export type { FileBrowserProps, FileNode } from "./file-browser";

export { ConfirmModal } from "./confirm-modal";
export type { ConfirmModalProps } from "./confirm-modal";

export { Dropdown } from "./dropdown";
export type { DropdownProps, DropdownItem } from "./dropdown";

export { FileTabs } from "./file-tabs";
export type { FileTabsProps, FileTab } from "./file-tabs";

export { MediaViewer } from "./media-viewer";
export type { MediaViewerProps, MediaFileType } from "./media-viewer";

export { RecentPane } from "./recent-pane";
export type { RecentPaneProps, RecentEntry } from "./recent-pane";

export { Tooltip } from "./tooltip";
export type { TooltipProps } from "./tooltip";

// Bridge runtime for app docking
export {
  installFetchOverride,
  mountReactApp,
  unmountReactApp,
  emitBridgeEvent,
  onBridgeEvent,
} from "./bridge";
export type {
  BridgeConfig,
  BridgeMountOptions,
  AppMounter,
  AppUnmounter,
} from "./bridge";
