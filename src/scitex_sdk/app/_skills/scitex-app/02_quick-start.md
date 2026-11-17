# Start with the SDK workflow

Start with [what the user wants to build](../../../_skills/scitex-sdk/05_build-from-intent.md),
then read the SDK workflow and app/UI contract. Published leaf GUIs
belong to `src/<leaf_pkg>/_django` and own their configuration, manifest,
views, URLs, templates and assets. Hub mounts these generically and supplies
authorized capabilities. Standalone runs the same view implementation with
an explicit local project root.

Import `scitex_sdk.app.embed.ScitexAppConfig` for the leaf configuration.
Django templates extend `scitex_sdk/app/app_shell.html`, fill the stable
`scitex_app_content` block and load assets from `scitex_sdk/ui/...`.
Preserve database labels, CSRF and project/path refusal behavior. Verify
both mounting modes and installed artifacts before replacing a host route.

For a new application, `scitex-sdk app init ./sample_app --name sample_app
--dry-run` previews the boilerplate plan. Create only after choosing an owned
destination; preserve existing projects. The scaffold does not implement the
user's requested domain feature. Existing leaf GUIs need no new scaffold.

The optional creator, `scitex-sdk gui serve` (default port31301), starts with
the user's description and creates a plain workspace containing that brief.
It does not implement the requested feature. The CLI creation/validation tools
are `scitex-sdk app init` and `validate`; `install-dev` and `submit` require
the normal host/release workflow. Structural validation does not replace
behavioral tests or actual visual verification. Installed/hosted adoption must
be checked separately; older versions can still show starter cards.
