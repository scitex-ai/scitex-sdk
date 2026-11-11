# SDK UI components Python API

Import the canonical namespace: `scitex_sdk.ui`. Use the installed
package's public API and source for signatures; do not assume an old
App/UI distribution or private host module is present.

The App contract supplies `get_files`, the `FilesBackend` protocol, public
embed helpers and plugin discovery via `scitex_sdk.app.plugins`.
The UI namespace supplies `get_component`, `list_components`,
`register_component`, `get_static_dir` and `get_docs_path`.
`scitex_sdk.get_frontend_package_dir()` locates the packaged `@scitex/sdk`
npm manifest in either a checkout or wheel. CSS, TS and React exports live
under `@scitex/sdk/ui/...`; use packed file links for React peer resolution.

Hosted file operations use authorized host capabilities. Project selection
and a client-controlled ID never grant storage access.

## Frontend request tokens

```typescript
import { csrfToken } from "@scitex/sdk/ui/ts";
```

For same-origin mutations, send this value in `X-CSRFToken`. The helper prefers
Django's rendered `input[name="csrfmiddlewaretoken"]`, so hosts can retain
HttpOnly CSRF cookies. It falls back to the readable `csrftoken` cookie for
standalone hosts, and returns an empty string when neither source is available
or no browser document exists. The host still validates every request; this
helper does not disable CSRF or grant project access. The HTTP project provider
uses the same helper for project and scope persistence.
