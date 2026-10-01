"""Current SDK guidance embedded in generated custom applications."""

def _platform_docs_md(name: str) -> str:
    return f"""# {name}: standalone and hosted GUI

This custom-app scaffold keeps its existing flat package layout for loader
compatibility. Published leaf packages keep their Django GUI under
`src/<leaf_pkg>/_django`; both use the same SDK contracts.

`scitex-sdk` owns the App/UI implementation. `apps.py` subclasses
`scitex_sdk.app.embed.ScitexAppConfig`; `urls.py` and `views.py` belong to this
application. Templates extend `scitex_sdk/app/app_shell.html` and fill the
stable `scitex_app_content` block. The package declares a `scitex.apps` entry
point naming its Django AppConfig.

The host mounts that entry point generically and supplies authenticated
capabilities. Import SDK contracts rather than Hub implementation modules.
Use the host's authorized project/storage provider; selection alone does not
grant access. Standalone file operations require an explicit local root.

Read the bundled SDK workflow skill before implementation. Verify current
source and observed behavior, then use SDK CLI/MCP execution interfaces.
For development, install this app with its `scitex` extra and use
`scitex-sdk app validate {name}`. Run the same views in standalone and plugin
modes before release or cutover. All test data must be owned synthetic data.

The SDK package metadata defines its license and dependency versions.
Available Hub features depend on the installed host; verify them before
documenting a deployment or publication workflow.
"""
