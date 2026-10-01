/**
 * Which KIND of attachment is this? — the classification half of rendering.
 *
 * WHY THIS AND NOT A SHARED RENDERER. orochi and scitex-ui both render
 * attachments, and the obvious move — one side adopting the other's renderer —
 * does not work: theirs concatenates an HTML string, ours returns DOM nodes.
 * Adoption would mean rewriting a renderer to delete a handful of lines, which
 * orochi measured and correctly declined.
 *
 * But the string-vs-DOM split is in the OUTPUT. The decision that comes first —
 * "is this an image, a video, a PDF, or a file?" — has no return type to
 * disagree about. That decision is duplicated in both codebases, is pure, and
 * is the part that actually goes wrong: every consumer invents its own
 * `startsWith("image/")` ladder and each one forgets a different case.
 *
 * So this ships the classifier alone. A caller keeps its own renderers and
 * keys them off `attachmentKind()`, which is how one taxonomy can serve a
 * DOM-returning renderer and a string-returning one at the same time.
 *
 * The kinds are taken from orochi's seven live branches (image, image grid,
 * video, audio, PDF, text/markdown, fallback file) rather than invented — the
 * grid is a layout choice over several images, not a kind, so it is theirs.
 */

/** Distinct presentations an attachment can need. Ordered most→least specific. */
export type AttachmentKind =
  | "image"
  | "video"
  | "audio"
  | "pdf"
  | "text"
  | "file";

/** Extensions that outrank a vague or absent MIME type. */
const EXTENSION_KINDS: ReadonlyArray<readonly [RegExp, AttachmentKind]> = [
  [/\.pdf$/i, "pdf"],
  [/\.(md|markdown|txt|log|csv|tsv|rst)$/i, "text"],
  [/\.(png|jpe?g|gif|webp|avif|bmp|svg)$/i, "image"],
  [/\.(mp4|webm|mov|mkv|avi)$/i, "video"],
  [/\.(mp3|wav|ogg|flac|m4a|aac)$/i, "audio"],
];

/**
 * Classify by MIME type, falling back to the filename extension.
 *
 * @param mime      e.g. "image/png". Empty or absent is normal — a server that
 *                  does not know sends `application/octet-stream`, which is
 *                  "some bytes", not "a file the user thinks of as generic".
 * @param filename  consulted when the MIME type is missing or uninformative.
 *
 * Returns "file" when nothing else matches. That is a real answer, not a
 * failure: a chip with a name and a download link is the correct presentation
 * for an unknown type.
 */
export function attachmentKind(mime?: string | null, filename?: string | null): AttachmentKind {
  const type = (mime ?? "").trim().toLowerCase();

  // PDF before the generic `application/*` fallthrough, because it has a
  // presentation of its own (first-page thumbnail) that a file chip lacks.
  if (type === "application/pdf") return "pdf";

  // Markdown and friends arrive as text/* but so does text/html, which is not
  // something to preview inline as prose.
  if (type.startsWith("text/") && type !== "text/html") return "text";

  if (type.startsWith("image/")) return "image";
  if (type.startsWith("video/")) return "video";
  if (type.startsWith("audio/")) return "audio";

  // Only NOW consult the extension. An explicit, specific MIME type is a
  // stronger signal than a filename, which is user-supplied and often wrong —
  // but `application/octet-stream` carries no information at all, so a
  // ".pdf" suffix beats it.
  const name = (filename ?? "").trim();
  if (name) {
    for (const [pattern, kind] of EXTENSION_KINDS) {
      if (pattern.test(name)) return kind;
    }
  }

  return "file";
}
