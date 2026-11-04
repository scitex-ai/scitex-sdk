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

In-app headers use one shared appearance across apps. See the
[header contract and browser checks](docs/ui/app-header-contract.md).
Shared filter fields follow the [filter contract](docs/ui/filter-field-contract.md).

```bash
# Install the GUI runtime for SDK 0.3.0 or newer.
pip install 'scitex-sdk[gui]>=0.3.0'
scitex-sdk app --help
scitex-sdk ui --help
scitex-sdk gui serve
```

Add the `chat`, `mcp`, `cli` or `project` extras for those capabilities, or
install `scitex-sdk[all]`. The `project` and `cli` extras, `all`, and contributor
tooling require scitex-dev>=0.62.6
for the declared UI provider replacement SPI. SDK publication verifies a normal built-wheel `[all]`
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

Since 0.3.3 the SDK declares the replacement of the exact legacy UI
linter provider (UI-101..107, now the UI-101..114 corpus). Both
distributions may remain installed while a compatible Dev registers the
rules; standalone SDK UI use keeps Dev optional. See [provider transition
(completed)](docs/UI_LINTER_PROVIDER_TRANSITION.md).

Web API descriptor quality is enforced by the SDK-owned `PS-SDK-WEB` project auditor and hooks. See [Web API contract enforcement](src/scitex_sdk/app/_skills/scitex-app/24_web-api-contract.md) for source-only guarantees and host-admission boundaries.

The SDK declares an opt-in read-only Web `skills` operation over its bundled
SDK/App/UI documentation. Python callers can use
`scitex_sdk.list_bundled_skills()` directly. This reads package resources only;
it does not discover user skills or enable a hosted route. See the
[Python API catalog](src/scitex_sdk/_skills/scitex-sdk/03_python-api.md).

The five interfaces have distinct discovery paths:

| Interface | Discover the SDK surface |
|---|---|
| Python | `scitex_sdk.app`, `scitex_sdk.ui`, `scitex_sdk.project`; `scitex-sdk list-python-apis --json` |
| CLI | `scitex-sdk --help`, then `app --help` or `ui --help` |
| MCP | `scitex-sdk mcp list-tools` for the App/UI tool catalog |
| Web API | The `scitex.apis` entry point names an `ApiPlugin` data object; inspect its `openapi_fragment()` in a trusted SDK environment |
| Skills | `scitex-sdk skills list --json` and the installed `scitex_dev.skills` providers |

<sub><b>Table 1.</b> SDK interface discovery; host admission and live availability are checked separately.</sub>

Dev owns generic interface presence and dispatch. The SDK supplies Web
descriptor quality checks through that dispatcher; leaves keep their domain
logic and handlers. Source declarations, installed providers, host admission,
and a reachable server are separate observations. A host must explicitly admit
a descriptor before resolving handlers; publishing or discovering it alone
does not enable an endpoint.
