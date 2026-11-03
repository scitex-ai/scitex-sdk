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
is not authorization, and client-controlled IDs do not grant storage access. An optional
provider `canonical_project_id(request, selector)` may translate a legacy
selector; SDK accepts the result only when it is in this request's accessible
project list. Storage and persistence receive the canonical ID, and denied
aliases never fall back to a stored project.

`scitex_sdk.host` supplies the shared access errors, authorized project and
private store capability records, and host-provider resolution helpers.
`scitex_sdk.local` supplies explicitly configured single-user standalone
providers. Neither module certifies PostgreSQL tenant isolation or supplies
an ambient database connection when a provider is absent.

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
but the database app label remains `scitex_app` (the model-less ui component
carries the namespaced `scitex_sdk_ui` label and has no database identity);
chat foreign keys
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
The `project`, `cli`, and `all` extras require the Dev version declared in
`pyproject.toml` (currently `scitex-dev>=0.62.6`). Use a normal extras install
and `pip check` to qualify the dependency graph.

## Web API contracts and agent discovery

Leaf packages declare real `ApiPlugin` objects through `scitex.apis`; the SDK
owns their route, schema, operation-ID and scope contracts. Dev discovers the
SDK's `PS-SDK-WEB` project auditor and native hooks through the existing
`scitex_dev.audit.project` and `scitex_dev.hooks` providers. It owns generic
interface presence; it does not replace leaf domain behavior.

Read the bundled [Web API contract](../app/_skills/scitex-app/24_web-api-contract.md)
for source-only checks, inert distribution metadata and explicit host admission.
The SDK's own example is a read-only bundled-skills catalog. A declaration or
passing source audit does not prove an installed provider, enabled route or
live server. Discover Python, CLI, MCP and skills through the
[SDK workflow](../_skills/scitex-sdk/SKILL.md).

## Layout doctrine: main content vs Details pane

Reduced cognitive load is a layout rule, not a suggestion. The main
pane carries the critical path and nothing else. Everything uncritical
— metadata, diagnostics, secondary actions, audit trails — lives in
the Details pane (right-edge strip / drawer / collapsible panel from
`scitex_sdk.ui`), keeping strict separation from main contents.
Scholar's right-edge Details strip is the reference; writer's details
patterns follow it. This is review-enforced: criticality cannot be
measured statically, so no linter rule covers it — reviewers check
placement, the SDK supplies the primitives.

iOS and Android native delivery is a future target, not a shipped feature.


### Installed Web API metadata

A `scitex.apis` declaration must also be serialized into the wheel's dist-info
for metadata-only host discovery. Use the SDK-owned build producer and standard
Hatch adapter; do not import the consumer or maintain duplicate descriptor JSON.
See [the Web API build recipe](../app/_skills/scitex-app/24_web-api-contract.md#build-the-installed-declaration).
Missing installed metadata remains unknown and never implies host admission.
