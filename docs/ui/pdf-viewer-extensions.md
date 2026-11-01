# PDF page extension surface

`@scitex/sdk/ui/pdf-viewer` owns page rasterization, pen geometry, and optional
PDF.js text/link layers. Importing it stays inert. Existing two-argument
`onPageRender(page, viewport)` callbacks continue to work.

The optional third argument is `PdfPageSurface`: its `element` is the owned
page mount, and `pdfToViewportPoint`, `pdfToViewportRect`, and
`viewportToPdfPoint` preserve PDF.js rotation/crop/scale transforms. PDF
coordinates use bottom-left origin and PDF units; page numbers start at 1.
Attach rich overlays to this public mount, never query private canvas DOM.
Zoom replaces mounts, so reattach in the page-render hook. Consumers own
all overlay/comment data, policies, URLs, and persistence.

Enable `textLayer: true` for selectable/searchable PDF text and
`linkLayer: true` for safe external links and internal page destinations.
Both default to false for existing pen-only consumers. The pen layer captures
input only while interactive; `setInteractive(false)` exposes text and links.
PDF form editing is not provided.

Direct browser consumers may load the generated public
`scitex_sdk/ui/js/app/pdf-viewer.js` using Django `app_static` and pass their
already-loaded `pdfjs` module plus its `workerSrc`. This avoids a duplicate
vendor copy. Npm/bundled consumers normally use the declared `pdfjs-dist`
dependency. The direct ESM asset leaves that dynamic import external, so
provide `pdfjs` (or a browser import map) when using it without a bundler.

Rebuild the browser asset with `npm run build:ui -- --only js/app/pdf-viewer.js`.
`tests/scitex_sdk/ui/check_pdf_viewer_browser.py` exercises actual PDF.js with
a disposable two-page PDF, rotated crop box, text selection, internal link,
scale replacement, conversion round-trip and teardown. It requires the
explicit `--chromium` path and does not read live research projects.
