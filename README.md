# scitex-sdk

One implementation owner for SciTeX app contracts and UI components:
`scitex_sdk.app` and `scitex_sdk.ui`. The SDK ships the Python code, Django
templates/static assets, translations, and packaged `@scitex/sdk` frontend.

```python
from scitex_sdk.app import get_files
from scitex_sdk.app.embed import ScitexAppConfig, run_standalone
from scitex_sdk import ui, get_frontend_package_dir
```

Leaf apps own their GUI under `src/<leaf_pkg>/_django`, use this SDK, and run
standalone or as a plugin. Hub mounts apps generically and supplies authorized
capabilities. See the [app/UI contract](src/scitex_sdk/_docs/APP_DEVELOPER_GUIDE.md)
and [workflow skill](src/scitex_sdk/_skills/scitex-sdk/SKILL.md).

```bash
pip install 'scitex-sdk[gui,chat,mcp,cli]'
scitex-sdk app --help
scitex-sdk ui --help
scitex-sdk gui serve
```

Contributor dependencies use `pip install -e . --group dev`. The `project`
and `all` extras require published scitex-dev>=0.62.0; publication of that
API remains a release prerequisite. Version 0.3.0 is a consolidation candidate,
not a claim that a release, deployment or repository archival has happened.

Migration changes imports to `scitex_sdk.app/ui` and resource prefixes to
`scitex_sdk/app/` and `scitex_sdk/ui/`. Existing Django database labels,
template block names and App/UI environment settings retain their identity.
Old App/UI repositories will be public archives after consumer migration.
