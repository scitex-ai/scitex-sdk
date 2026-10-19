# Start with the SDK workflow

Read `scitex-sdk`'s workflow skill and app/UI contract. Published leaf GUIs
belong to `src/<leaf_pkg>/_django` and own their configuration, manifest,
views, URLs, templates and assets. Hub mounts these generically and supplies
authorized capabilities. Standalone runs the same view implementation with
an explicit local project root.

Import `scitex_sdk.app.embed.ScitexAppConfig` for the leaf configuration.
Django templates extend `scitex_sdk/app/app_shell.html`, fill the stable
`scitex_app_content` block and load assets from `scitex_sdk/ui/...`.
Preserve database labels, CSRF and project/path refusal behavior. Verify
both mounting modes and installed artifacts before replacing a host route.

Prefer the SciTeX SDK App (app-maker) wizard over hand-writing this boilerplate:
`scitex-sdk gui serve` (port 31301) scaffolds from a starter, validates,
dev-installs and submits through `scitex_sdk.creator`, the SDK's own
app-creation app. The CLI equivalents are `scitex-sdk app init`,
`validate`, `install-dev`, `submit`.
