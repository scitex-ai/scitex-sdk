/**
 * scitex-ui CSS index builder
 *
 * Auto-generates all.css, shell.css, and app.css by scanning the directory.
 * Run: npx tsx css/_build-index.ts
 */

import { readdirSync, statSync, writeFileSync } from "fs";
import { join, relative, dirname } from "path";

const CSS_DIR = dirname(new URL(import.meta.url).pathname);

function findCssFiles(dir: string, base: string = dir): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry.startsWith("_") || entry === "node_modules") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...findCssFiles(full, base));
    } else if (
      entry.endsWith(".css") &&
      !["all.css", "shell.css", "app.css"].includes(entry)
    ) {
      files.push("./" + relative(base, full));
    }
  }
  return files.sort();
}

/**
 * Token-only primitives, prepended to app.css.
 *
 * app.css used to import nothing from primitives/, so every `--status-*`,
 * `--bg-secondary`, `--border-color` and `--success-color` referenced by an
 * app component resolved to NOTHING for anyone loading app.css alone. That is
 * why components ended up carrying literal hex fallbacks and why consumers
 * hard-code colours instead of inheriting the palette — the shared tokens
 * existed but were unreachable from the layer that needed them.
 *
 * Only the pure-`:root` files are listed. `primitives/typography.css` is
 * deliberately EXCLUDED: it carries 63 rule blocks including `body` and
 * `h1`-`h6`, so importing it here would restyle every consuming page rather
 * than define tokens.
 */
const APP_TOKEN_PRIMITIVES = [
  "./primitives/colors.css",
  "./primitives/spacing.css",
  "./primitives/typography-vars.css",
];

function buildIndex(name: string, subdirs: string[], prepend: string[] = []): void {
  const files: string[] = [...prepend];
  for (const subdir of subdirs) {
    const dir = join(CSS_DIR, subdir);
    try {
      files.push(...findCssFiles(dir, CSS_DIR));
    } catch {
      /* dir doesn't exist */
    }
  }

  const header = `/**
 * scitex-ui — ${name} CSS bundle (AUTO-GENERATED)
 *
 * Do not edit manually. Regenerate with: npx tsx css/_build-index.ts
 */\n\n`;

  const imports = files.map((f) => `@import "${f}";`).join("\n");
  writeFileSync(join(CSS_DIR, `${name}.css`), header + imports + "\n");
  console.log(`${name}.css: ${files.length} imports`);
}

buildIndex("shell", ["shell", "primitives"]);
buildIndex("app", ["app"], APP_TOKEN_PRIMITIVES);

// all.css = shell + app + utils
const allFiles = findCssFiles(CSS_DIR, CSS_DIR).filter(
  (f) =>
    !f.includes("_build") &&
    f !== "./all.css" &&
    f !== "./shell.css" &&
    f !== "./app.css",
);
const allHeader = `/**
 * scitex-ui — Complete CSS bundle (AUTO-GENERATED)
 *
 * Do not edit manually. Regenerate with: npx tsx css/_build-index.ts
 */\n\n`;
writeFileSync(
  join(CSS_DIR, "all.css"),
  allHeader + allFiles.map((f) => `@import "${f}";`).join("\n") + "\n",
);
console.log(`all.css: ${allFiles.length} imports`);
