# SDK App contract Python API

Import the canonical namespace: `scitex_sdk.app`. Use the installed
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
