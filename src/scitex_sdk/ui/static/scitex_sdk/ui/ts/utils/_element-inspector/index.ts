/**
 * Element Inspector - Barrel export
 *
 * Visual debugging tool for HTML elements.
 * Toggle with Alt+I, rectangle select with Ctrl+Alt+I,
 * debug snapshot with Ctrl+Shift+I.
 */

export * from "./types";
export { OverlayManager } from "./_overlay-manager";
export { ElementScanner } from "./_element-scanner";
export { DebugInfoCollector } from "./_debug-info-collector";
export { SelectionManager } from "./_selection-manager";
export { NotificationManager } from "./_notification-manager";
export { PageStructureExporter } from "./_page-structure-exporter";
export { ConsoleCollector } from "./_console-collector";
export { LabelRenderer } from "./_LabelRenderer";
export { LayerPickerPanel } from "./_LayerPickerPanel";
export type { HighlightCallback } from "./_LayerPickerPanel";
export { getDepth, getColorForDepth } from "./_depth-utils";
