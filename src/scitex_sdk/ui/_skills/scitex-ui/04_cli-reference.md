# SDK UI components execution tools

Read the SDK workflow skill first. CLI and MCP execute that workflow;
they do not replace the application ownership and authorization contract.

Use `scitex-sdk ui --help` for the actual installed command tree.
App development verbs are under `scitex-sdk app`; UI tooling is under
`scitex-sdk ui`; the creator uses `scitex-sdk gui` with explicit verbs.
For MCP configuration, inspect `scitex-sdk ui mcp show-installation --json`.
Those configurations launch the canonical SDK executable and component args.

Verify current command signatures, optional dependencies and output before
documenting them. The archived-source App/UI executables are not required.
