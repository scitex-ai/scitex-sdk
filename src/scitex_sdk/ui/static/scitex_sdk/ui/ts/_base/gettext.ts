/**
 * Django-compatible client translations: gettext, ngettext, pgettext, npgettext,
 * interpolate, gettext_noop, pluralidx — the same names as Django's JS catalog.
 *
 * Catalogs come from `{% scitex_js_catalog "<app package>" %}` (scitex_sdk.ui.i18n),
 * which renders the active language's djangojs catalog as json_script. With no
 * catalog on the page every function returns the English msgid unchanged.
 */

export const JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-";

export type CatalogEntry = string | string[];

export interface JsCatalogPayload {
  language?: string;
  plural?: string | null;
  catalog: Record<string, CatalogEntry>;
}

interface CatalogState {
  entries: Record<string, CatalogEntry>;
  plural: string | null;
}

interface CatalogDocument {
  querySelectorAll(selectors: string): ArrayLike<{ textContent: string | null }>;
}

const CONTEXT_SEPARATOR = "\x04";

let state: CatalogState | null = null;

/** Merge a catalog payload into the active catalog; later payloads win on shared msgids. */
export function installCatalog(payload: JsCatalogPayload): void {
  const current = state ?? { entries: {}, plural: null };
  state = {
    entries: { ...current.entries, ...payload.catalog },
    plural: payload.plural ?? current.plural,
  };
}

/** Forget every installed catalog, returning to English passthrough. */
export function resetCatalog(): void {
  state = null;
}

/** Install every json_script catalog found in `doc`. */
export function loadCatalogsFromDocument(doc: CatalogDocument): void {
  const elements = doc.querySelectorAll(
    `script[type="application/json"][id^="${JS_CATALOG_ELEMENT_PREFIX}"]`,
  );
  for (const element of Array.from(elements)) {
    installCatalog(JSON.parse(element.textContent || "{}") as JsCatalogPayload);
  }
}

function activeCatalog(): CatalogState {
  if (state === null) {
    state = { entries: {}, plural: null };
    // Lazy first read so a module imported before the catalog tag still finds it.
    if (typeof document !== "undefined") loadCatalogsFromDocument(document);
  }
  return state;
}

export function gettext(msgid: string): string {
  const entry = activeCatalog().entries[msgid];
  if (entry === undefined) return msgid;
  const translated = typeof entry === "string" ? entry : entry[0];
  return translated || msgid;
}

export function gettext_noop(msgid: string): string {
  return msgid;
}

export function pluralidx(count: number): number {
  const expression = activeCatalog().plural;
  if (!expression) return count === 1 ? 0 : 1;
  return Number(evaluatePluralExpression(expression, count));
}

export function ngettext(singular: string, plural: string, count: number): string {
  const entry = activeCatalog().entries[singular];
  const fallback = count === 1 ? singular : plural;
  if (entry === undefined) return fallback;
  if (typeof entry === "string") return entry || fallback;
  return entry[pluralidx(count)] || fallback;
}

export function pgettext(context: string, msgid: string): string {
  const translated = gettext(context + CONTEXT_SEPARATOR + msgid);
  return translated.includes(CONTEXT_SEPARATOR) ? msgid : translated;
}

export function npgettext(
  context: string,
  singular: string,
  plural: string,
  count: number,
): string {
  const translated = ngettext(
    context + CONTEXT_SEPARATOR + singular,
    context + CONTEXT_SEPARATOR + plural,
    count,
  );
  if (!translated.includes(CONTEXT_SEPARATOR)) return translated;
  return count === 1 ? singular : plural;
}

/** Django's interpolate: `%s` from an array, or `%(name)s` from an object when `named`. */
export function interpolate(
  format: string,
  values: unknown[] | Record<string, unknown>,
  named = false,
): string {
  if (named) {
    const byName = values as Record<string, unknown>;
    return format.replace(/%\(\w+\)s/g, (token) => String(byName[token.slice(2, -2)]));
  }
  const positional = [...(values as unknown[])];
  return format.replace(/%s/g, () => String(positional.shift()));
}

/** Evaluate a gettext Plural-Forms expression (C syntax over `n`) without eval. */
export function evaluatePluralExpression(expression: string, n: number): number {
  const tokens = expression.match(/\d+|n|&&|\|\||[=!<>]=|[<>!?:%()]/g) ?? [];
  let position = 0;
  const peek = (): string | undefined => tokens[position];
  const take = (): string => tokens[position++];

  const parsePrimary = (): number => {
    const token = take();
    if (token === "(") {
      const value = parseTernary();
      take();
      return value;
    }
    if (token === "!") return Number(!parsePrimary());
    if (token === "n") return n;
    return Number(token);
  };
  const parseBinary = (operators: string[], next: () => number): (() => number) => {
    return () => {
      let left = next();
      while (operators.includes(peek() ?? "")) {
        const operator = take();
        const right = next();
        left = applyOperator(operator, left, right);
      }
      return left;
    };
  };
  const parseModulo = parseBinary(["%"], parsePrimary);
  const parseRelational = parseBinary(["<", "<=", ">", ">="], parseModulo);
  const parseEquality = parseBinary(["==", "!="], parseRelational);
  const parseAnd = parseBinary(["&&"], parseEquality);
  const parseOr = parseBinary(["||"], parseAnd);
  function parseTernary(): number {
    const condition = parseOr();
    if (peek() !== "?") return condition;
    take();
    const whenTrue = parseTernary();
    take();
    const whenFalse = parseTernary();
    return condition ? whenTrue : whenFalse;
  }
  return parseTernary();
}

function applyOperator(operator: string, left: number, right: number): number {
  switch (operator) {
    case "%":
      return left % right;
    case "<":
      return Number(left < right);
    case "<=":
      return Number(left <= right);
    case ">":
      return Number(left > right);
    case ">=":
      return Number(left >= right);
    case "==":
      return Number(left === right);
    case "!=":
      return Number(left !== right);
    case "&&":
      return Number(Boolean(left) && Boolean(right));
    default:
      return Number(Boolean(left) || Boolean(right));
  }
}
