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
# Install the GUI runtime for SDK 0.3.0 or newer.
pip install 'scitex-sdk[gui]>=0.3.0'
scitex-sdk app --help
scitex-sdk ui --help
scitex-sdk gui serve
```

Add the `chat`, `mcp`, `cli` or `project` extras for those capabilities, or
install `scitex-sdk[all]`. The `project` and `all` extras require
scitex-dev>=0.62.0. SDK publication verifies a normal built-wheel `[all]`
installation and `pip check` against published dependencies before uploading.
Contributor dependencies use `pip install -e . --group dev`.

Migration changes imports to `scitex_sdk.app/ui` and resource prefixes to
`scitex_sdk/app/` and `scitex_sdk/ui/`. Existing Django database labels,
template block names and App/UI environment settings retain their identity.
The predecessor [App](https://github.com/scitex-ai/scitex-app) and
[UI](https://github.com/scitex-ai/scitex-ui) repositories are public archives.
Users coming from either one: start at
[docs/MIGRATION_FROM_APP_AND_UI.md](docs/MIGRATION_FROM_APP_AND_UI.md).
Sequential SDK publication can still observe transitive predecessor packages
and reports dependency retirement as incomplete. Consumer migration and strict
published dependency retirement remain separate gates; see
[the release sequence](docs/RELEASE_BOOTSTRAP.md).
