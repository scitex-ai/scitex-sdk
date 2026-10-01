/**
 * Where am I mounted?
 *
 * A SciTeX app runs at "/" standalone and under a prefix as a scitex-hub
 * built-in ("/apps/u/<module>/" for published apps; assorted prefixes for
 * the built-ins mounted in config/urls.py). The SERVER side already handles
 * both — scitex_app's urlpatterns are relative, so include() works anywhere.
 * What the browser never had was any way to LEARN the prefix, so client code
 * hardcoded "/", which is correct standalone and silently wrong embedded.
 *
 * This reads the prefix the server put in the page. It does NOT guess.
 *
 * WHY IT THROWS RATHER THAN DEFAULTING TO "/":
 * a default is indistinguishable from a correct answer at the only moment it
 * matters. An app whose marker is missing would work perfectly in every
 * standalone test and fail only once embedded — which is the exact bug this
 * exists to remove. scitex-cards reached the same conclusion independently
 * and their chat.js says so: "a missing marker is an integration bug, never
 * a silently-guessed root mount."
 *
 * TWO ACCEPTED SPELLINGS, one reader:
 *   1. <body data-api-base="/apps/cards/">     scitex-cards ships this today
 *   2. <meta name="stx-mount" content="...">   scitex_app injects this
 *
 * That is deliberate and it is not two implementations. scitex-cards renders
 * through Django templates, where an attribute on <body> is natural.
 * scitex_app's `scitex_editor_page` serves a BUILT SPA with read_text(), so
 * it must insert into an existing document — and inserting a <meta> into
 * <head> is far safer there than rewriting a <body> tag that may carry
 * attributes, may be uppercase, or may be absent. One contract, one reader,
 * one documented precedence; the spelling follows what each server can
 * safely emit.
 */

/** Attribute scitex-cards already ships. Checked first — it is in production. */
export const MOUNT_ATTRIBUTE = "data-api-base";

/** Meta name scitex_app injects into built SPA documents. */
export const MOUNT_META_NAME = "stx-mount";

export class MountPrefixMissingError extends Error {
  constructor() {
    super(
      "scitex-ui: no mount marker found. The page must carry either " +
        `<body ${MOUNT_ATTRIBUTE}="…"> or ` +
        `<meta name="${MOUNT_META_NAME}" content="…">, ` +
        "set server-side from request.path. This is an integration bug — " +
        "scitex-ui will not guess a root mount, because a wrong guess works " +
        "standalone and fails only once embedded.",
    );
    this.name = "MountPrefixMissingError";
  }
}

/** Normalise to a form safe to join paths onto: no trailing slash, "" for root. */
function normalise(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  return trimmed;
}

/**
 * The prefix this app is mounted under, without a trailing slash.
 * Root mount returns "" so `${mountPrefix()}/api/x` is always well-formed.
 *
 * @throws MountPrefixMissingError when the page carries no marker.
 */
export function mountPrefix(doc: Document = document): string {
  const attr = doc.body?.getAttribute(MOUNT_ATTRIBUTE);
  if (attr !== null && attr !== undefined) return normalise(attr);

  const meta = doc.querySelector(`meta[name="${MOUNT_META_NAME}"]`);
  const content = meta?.getAttribute("content");
  if (content !== null && content !== undefined) return normalise(content);

  throw new MountPrefixMissingError();
}

/**
 * Join an app-relative path onto the mount prefix.
 * `apiUrl("/api/items")` -> "/api/items" standalone, "/apps/cards/api/items"
 * when mounted under "/apps/cards/".
 */
export function apiUrl(path: string, doc: Document = document): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${mountPrefix(doc)}${suffix}`;
}
