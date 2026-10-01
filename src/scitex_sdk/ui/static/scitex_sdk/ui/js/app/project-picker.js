/**
 * @deprecated — use `scitex_ui/js/app/project-selector.js` instead.
 *
 * This file is the OLD entry name for the project picker. The distributable
 * entry is now `project-selector.js` (built from ts/app/project-selector/
 * auto-mount.ts, the SAME component this used to bundle). Keeping
 * `project-picker.js` as a thin alias means pages still loading the old name
 * keep working until they migrate — but new code must import
 * `project-selector.js`. The alias is scheduled for removal in a major
 * release; the single discoverable name is `project-selector`.
 *
 * Importing this module loads the canonical bundle, which auto-mounts every
 * `[data-stx-project-picker]` element exactly as before — the behaviour is
 * unchanged, only the file name is being retired.
 */
import "./project-selector.js";
