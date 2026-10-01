# SciTeX SDK app and UI contract

`scitex-sdk` owns `scitex_sdk.app`, `scitex_sdk.ui`, their templates,
static assets and frontend exports. Apps import this distribution directly.
The App and UI repositories are migration sources pending public archival;
their existing PyPI releases remain historical artifacts.

Leaf packages own their GUI at `src/<leaf_pkg>/_django`. A leaf supplies its
Django app configuration, manifest, URLs, views, templates and assets. Hub
discovers and mounts that app and supplies authenticated user, project,
storage and job capabilities. Hub must not implement leaf domain operations
or choose a substitute project when authorization fails. Project selection
is not authorization, and client-controlled IDs do not grant storage access.

Use the same leaf URL/view implementation for standalone and Hub plugin
modes. Standalone chooses an explicit local project root; a hosted app uses
only the capabilities supplied by its host. Keep write permission checks,
CSRF checks and path confinement in the common implementation. Existing
quality gates must pass before replacing a Hub route.

```python
from scitex_sdk.app.embed import ScitexAppConfig, run_standalone
from scitex_sdk.app import get_files
from scitex_sdk.ui.project_scope import host_project_provider
```

Django installs `scitex_sdk.app` and `scitex_sdk.ui`. Their Python names move,
but database app labels remain `scitex_app` and `scitex_ui`; chat foreign keys
and the `scitex_app_content` template block retain their identity. Template
tag library filenames also remain stable. New template/static paths are
`scitex_sdk/app/...` and `scitex_sdk/ui/...`. Existing SCITEX_APP_* and
SCITEX_UI_* settings and configuration locations remain supported.

```django
{% extends "scitex_sdk/app/app_shell.html" %}
{% load static %}
{% block scitex_app_content %}Your leaf GUI{% endblock %}
```

`scitex_sdk.get_frontend_package_dir()` returns the packaged `@scitex/sdk`
npm directory. Resolve `@scitex/sdk/ui`, `@scitex/sdk/ui/react` and component
subpaths through its exports; `scitex_sdk.ui.get_static_dir()` returns its
UI assets. Both work from a wheel or checkout without sibling repositories.
A generated npm `file:` dependency names the current Python environment:
regenerate it and its lockfile after moving to another environment.
Use `npm install --install-links` (generated scaffolds set this in `.npmrc`)
so React peers resolve from the frontend's dependency tree.
Do not claim this private source package is an npm registry release.

Start with the relevant bundled skill and inspect current source and runtime
before changing an app. Skills explain workflow and invariants; CLI and MCP
are execution interfaces used within that workflow. Use `scitex-sdk app`
for app development and `scitex-sdk ui` for UI tooling. Install optional
dependencies for the capability being used (`gui`, `chat`, `mcp`, `cli`).
The `project` and `all` extras require a genuine published Dev>=0.62 API;
the consolidation release is held until that upstream requirement resolves.

iOS and Android native delivery is a future target, not a shipped feature.
