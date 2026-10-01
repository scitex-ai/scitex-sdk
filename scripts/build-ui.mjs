/** Rebuild UI browser bundles from their owning TypeScript entry points.
 *
 * Keep each existing ESM/IIFE contract. Hand-written combobox.js exposes
 * window.STX.Combobox; standalone-shell-init.js and the deprecated picker
 * are also hand-written and intentionally absent from this build table.
 *
 * Run npm run build:ui, or npm run build:ui -- --only js/utils/element-inspector.js.
 */
import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const staticRoot = fileURLToPath(
  new URL("../src/scitex_sdk/ui/static/scitex_sdk/ui/", import.meta.url),
);

const entries = [
  ["app/action-bar/auto-mount", "app/action-bar"],
  ["app/app-header/auto-mount", "app/app-header"],
  ["app/app-help/auto-mount", "app/app-help"],
  ["app/app-launcher/index", "app/app-launcher"],
  ["app/attachment/index", "app/attachment"],
  ["app/confirm-modal/index", "app/confirm-modal"],
  ["app/context-menu/index", "app/context-menu"],
  ["app/dim/index", "app/dim"],
  ["app/drawer/index", "app/drawer"],
  ["app/dropdown/index", "app/dropdown"],
  ["app/empty/index", "app/empty"],
  ["app/file-tabs/index", "app/file-tabs"],
  ["app/import-export/index", "app/import-export"],
  ["app/panes/auto-mount", "app/panes"],
  ["app/project-selector/auto-mount", "app/project-selector"],
  ["app/receipt/index", "app/receipt"],
  ["app/reply-quote/index", "app/reply-quote"],
  ["app/selector-nav/auto-mount", "app/selector-nav"],
  ["app/toast/index", "app/toast"],
  ["app/tooltip/index", "app/tooltip"],
  ["app/tour-player/auto-mount", "app/tour-player"],
  ["shell/app-scope-selector", "shell/app-scope-selector"],
  ["shell/launcher-overlay", "shell/launcher-overlay", "iife"],
  ["shell/mobile-swipe", "shell/mobile-swipe", "iife"],
  ["utils/element-inspector", "utils/element-inspector", "iife"],
];

const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== "--only")) {
  throw new Error("Usage: node scripts/build-ui.mjs [--only js/<bundle>.js]");
}
const selected = args.length
  ? entries.filter(([, out]) => `js/${out}.js` === args[1])
  : entries;
if (!selected.length) throw new Error(`Unknown generated UI bundle: ${args[1]}`);

for (const [source, output, format = "esm"] of selected) {
  const entry = `ts/${source}.ts`;
  const outfile = `js/${output}.js`;
  await build({
    absWorkingDir: staticRoot,
    entryPoints: [entry],
    outfile: resolve(staticRoot, outfile),
    bundle: true,
    format,
    platform: "browser",
    banner: {
      js: `/* AUTO-GENERATED from ${entry} via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only ${outfile} */`,
    },
    logLevel: "info",
  });
}
