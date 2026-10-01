/**
 * Drawer — off-canvas panel with a scrim.
 *
 *   import { createDrawer } from "scitex-ui/ts/app/drawer";
 *
 *   const drawer = createDrawer({
 *     panel: document.getElementById("agents"),
 *     trigger: document.getElementById("menu-btn"),
 *     side: "left",
 *   });
 *
 *   drawer.open();
 *   drawer.close();
 *   drawer.toggle();       // also wired to `trigger` automatically
 *
 * Closed means `inert`, not merely translated off-screen: a transformed panel
 * is invisible but still tabbable, which is how focus disappears into a closed
 * drawer. Escape closes, focus moves in on open and back out on close, and Tab
 * is trapped while open.
 *
 * The scrim is created and owned here — no `<div id="scrim">` needed in the
 * template.
 *
 * Styling: `css/app/drawer.css` (pair with `css/shell/theme.css` for tokens).
 */

export { Drawer, createDrawer } from "./_Drawer";
export { DRAWER_SIDES } from "./types";
export type { DrawerConfig, DrawerSide } from "./types";
