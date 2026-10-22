# Scaffold and validate a SciTeX app in five minutes

1. Scaffold: `scitex-sdk app init my-app` writes a complete app tree
   (manifest, URLconf, Django app) into `./my-app`.
2. Preview the SDK wizard: `scitex-sdk gui open` serves the creator UI
   (open/serve/status/stop verbs; `--dry-run` previews without starting).
3. Validate before dev-installing or publishing:
   `scitex-sdk app validate ./my-app` checks the manifest and readiness.
4. List the surface you just scaffolded against:
   `scitex-sdk list-python-apis` (both components) and
   `scitex-sdk mcp list-tools` (both MCP servers).

Scaffolding mechanics belong to the scitex-app skill (`app init`,
`app validate`, manifest contract); UI mounting to the scitex-ui skill
(shared AppHeader, tabs, project picker).
