"""HTML template generators for the SciTeX app scaffold."""

from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Django / Python file generators
# ---------------------------------------------------------------------------


def _apps_py(name, label, class_name):
    return f'''"""Django app configuration for {label}."""

from scitex_sdk.app.embed import ScitexAppConfig


class {class_name}Config(ScitexAppConfig):
    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "{name}"
    label = "{name}"
    verbose_name = "{label}"
'''


def _views_py(name, label, description):
    desc = description or f"A SciTeX Cloud app for {label}."
    return f'''"""Views for {label} workspace app."""

from __future__ import annotations

from django.shortcuts import render

from scitex_sdk.app.project_context import project_context
from scitex_sdk.ui.mount import mount_context


def build_{name}_context(request, current_project=None):
    """Context builder called by workspace registry for AJAX partial loads."""
    return {{
        "current_project": current_project,
        "app_name": "{label}",
        "app_description": "{desc}",
        "features": [
            "Workspace app integration",
            "AJAX partial loading",
            "Scoped CSS with theme variables",
        ],
    }}


def index_view(request):
    """Full page view for {label}."""
    shared_context = project_context(request)
    context = build_{name}_context(
        request, current_project=shared_context.get("active_project")
    )
    context.update(shared_context)
    context.update(mount_context(request, view_path=""))
    context["app_label"] = "{label}"
    return render(request, "{name}/index.html", context)


# EOF
'''


def _urls_py(name):
    return f'''"""URL configuration for {name}."""

from django.urls import path

from . import views

app_name = "{name}"

urlpatterns = [
    path("", views.index_view, name="index"),
]
'''


def _tests_py(name, label):
    module_name = name.removesuffix("_app")
    class_label = label.replace(" ", "")
    return f'''"""Tests for {label} workspace app."""

from django.test import SimpleTestCase


class {class_label}ContextTest(SimpleTestCase):
    """Unit tests for {label} context builder."""

    def test_context_has_required_keys(self):
        """Context builder returns all expected keys."""
        from django.test import RequestFactory
        from .views import build_{name}_context

        factory = RequestFactory()
        request = factory.get("/{name}/")

        ctx = build_{name}_context(request)
        self.assertIn("app_name", ctx)
        self.assertEqual(ctx["app_name"], "{label}")
        self.assertIn("app_description", ctx)
        self.assertIn("features", ctx)
        self.assertIsInstance(ctx["features"], list)


# EOF
'''


def _skill_py(name, label, description):
    desc = description or f"A SciTeX Cloud app for {label}."
    caps = _derive_capabilities(label, description)
    caps_str = json.dumps(caps, ensure_ascii=False)
    return f'''"""Skill registration for {label}."""

SKILL = {{
    "app_name": "{name}",
    "display_name": "{label}",
    "description": "{desc}",
    "capabilities": {caps_str},
}}
'''


def _derive_capabilities(label, description):
    """Derive 2-3 capabilities from description or use sensible defaults."""
    if not description:
        return [
            f"View {label} content",
            f"Interact with {label} workspace",
        ]
    words = description.lower()
    caps = [f"View {label} content"]
    if any(w in words for w in ("visual", "display", "plot", "chart", "graph")):
        caps.append(f"Visualize {label.lower()} data")
    if any(w in words for w in ("analy", "process", "comput", "calculat")):
        caps.append(f"Analyze {label.lower()} data")
    if any(w in words for w in ("edit", "creat", "write", "manag")):
        caps.append(f"Manage {label.lower()} resources")
    if len(caps) < 2:
        caps.append(f"Interact with {label} workspace")
    return caps[:3]


def _manifest_json(
    name, label, icon, description, extra_manifest, license_id, frontend_type="html"
):
    slug = name.replace("_", "-")
    desc = description or "A SciTeX Cloud app."
    manifest = {
        "$schema": "scitex-app-manifest",
        "$schema_version": "2.0.0",
        "name": name,
        "slug": slug,
        "label": label,
        "app_name": name,
        # SSoT: the app version derives at runtime from the installed
        # `pip_package` (the dist name) via importlib.metadata. A hand-written
        # `version` is forbidden by the validator — declare `pip_package`.
        "pip_package": slug,
        "icon": icon,
        "subtitle": desc[:80],
        "about": desc[:200],
        "description": desc,
        "author": "",
        "license": license_id,
        "keyboard_shortcut": "",
        "order": 50,
        "accent_color": "",
        "body_class": f"{slug}-page",
        "partial_template": f"{name}/index_partial.html",
        "context_builder": "",
        "ai_hint": desc,
        "capabilities": [],
        "allowed_extensions": [],
        "hidden_patterns": ["__pycache__", "node_modules", ".git", ".venv"],
        "privileges": [],
        "wip": True,
        "standalone": True,
        "standalone_command": f"{slug} gui",
        "standalone_port": 8050,
        "frontend_type": frontend_type,
        "dependencies": {
            "python": [],
            "system": [],
            "node": [],
            "r": [],
            "other": [],
        },
        "container": None,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# HTML template generators
# ---------------------------------------------------------------------------


def _index_html(name, label, *, include_js_bundle: bool = False):
    bundle_tag = ""
    if include_js_bundle:
        bundle_tag = f'\n    <script type="module" src="{{% static \'{name}/js/main.js\' %}}"></script>'
    return f"""{{% extends "scitex_sdk/app/app_shell.html" %}}
{{% load static %}}
{{% block extra_css %}}
    <link rel="stylesheet" href="{{% static '{name}/css/{name}.css' %}}">
{{% endblock %}}
{{% block extra_js %}}{bundle_tag}
{{% endblock %}}
{{% block scitex_app_content %}}
    {{% include "{name}/index_partial.html" %}}
{{% endblock %}}
"""


def _index_partial_html(name, label, icon, *, react_mount: bool = False):
    mount_div = ""
    if react_mount:
        mount_div = f'\n    <div id="{name}-root"></div>\n'
    return f"""{{% load static %}}
<div class="{name}-container" data-pane-type="app"
     data-ai-hint="Main container for {label} app">
    <div class="{name}-header" data-ai-hint="{label} app header">
        <h2><i class="{icon}"></i> {label}</h2>
        <p class="{name}-subtitle">Welcome to {label}. Edit this template to build your app.</p>
    </div>

    <div class="{name}-content" data-ai-hint="{label} content area">
        <div class="{name}-getting-started">
            <h3>Getting Started</h3>
            <ol class="{name}-steps">
                <li>
                    <strong>Build your UI</strong> &mdash;
                    Edit <code>templates/{name}/index_partial.html</code>
                </li>
                <li>
                    <strong>Add logic</strong> &mdash;
                    Update the context builder in <code>views.py</code>
                </li>
                <li>
                    <strong>Style it</strong> &mdash;
                    Customize <code>static/{name}/css/{name}.css</code>
                </li>
            </ol>
        </div>
{mount_div}
        <div class="{name}-placeholder">
            <i class="{icon}" style="font-size: 3rem; opacity: 0.3;"></i>
            <p>Your app content goes here.</p>
        </div>
    </div>
</div>
"""


def _app_css(name, label):
    return f"""/* Styles for {label} workspace app */

.{name}-container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
}}

.{name}-header {{
    margin-bottom: 1.5rem;
}}

.{name}-header h2 {{
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--workspace-text-primary);
    margin: 0 0 0.5rem;
}}

.{name}-subtitle {{
    font-size: 0.875rem;
    color: var(--workspace-text-secondary);
    margin: 0;
}}

.{name}-content {{
    background: var(--workspace-bg-secondary);
    border: 1px solid var(--workspace-border-default);
    border-radius: 6px;
    padding: 2rem;
}}

.{name}-getting-started {{
    margin-bottom: 2rem;
}}

.{name}-getting-started h3 {{
    font-size: 1.125rem;
    color: var(--workspace-text-primary);
    margin: 0 0 1rem;
}}

.{name}-steps {{
    padding-left: 1.25rem;
    color: var(--workspace-text-secondary);
    line-height: 1.8;
}}

.{name}-steps code {{
    background: var(--workspace-bg-tertiary);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8125rem;
}}

.{name}-card {{
    background: var(--workspace-bg-tertiary);
    border: 1px solid var(--workspace-border-default);
    border-radius: 6px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}}

.{name}-placeholder {{
    text-align: center;
    padding: 3rem 1rem;
    color: var(--workspace-text-secondary);
}}

.{name}-placeholder p {{
    margin: 0.5rem 0;
}}

@media (max-width: 768px) {{
    .{name}-container {{
        padding: 1rem;
    }}

    .{name}-content {{
        padding: 1rem;
    }}
}}
"""


def _agents_json(name, label):
    config = {
        "schemaVersion": 3,
        "instructions": {"path": "AGENTS.md"},
        "integrations": {
            "enabled": ["claude", "codex", "gemini", "cursor", "copilot_vscode"],
        },
        "syncMode": "source-only",
        "mcp": {
            "servers": {
                "scitex": {
                    "label": "SciTeX Platform",
                    "transport": "stdio",
                    "command": "/usr/local/bin/scitex",
                    "args": ["mcp", "start"],
                    "enabled": True,
                },
            }
        },
    }
    return json.dumps(config, indent=2) + "\n"


def _readme_md(name, label, description, license_id, *, frontend_type: str = "html"):
    desc = description or "A SciTeX Cloud App plugin."
    frontend_section = ""
    if frontend_type == "react":
        frontend_section = f"""
## Frontend (React)

The `frontend/` directory contains a React+Vite+Zustand setup.

```
frontend/
  package.json         # npm dependencies
  vite.config.ts       # Vite config (outputs to static/{name}/js/)
  tsconfig.json        # TypeScript config
  src/
    main.tsx           # Entry point — mounts <App /> to #{name}-root
    App.tsx            # Root component
    store/
      useAppStore.ts   # Zustand state store
```

### Development

```bash
cd frontend
npm install
npm run dev    # watch mode
npm run build  # production build
```
"""
    return f"""# {label}

{desc}

## Structure

```
{name}/
  __init__.py          # App init
  apps.py              # Django AppConfig
  views.py             # View functions and context builder
  urls.py              # URL routing
  tests.py             # Test suite
  skill.py             # Local agent metadata
  manifest.json        # App metadata
  templates/{name}/    # HTML templates
    index.html         # Full page (extends SDK shell)
    index_partial.html # AJAX-loadable partial
  static/{name}/css/   # Scoped stylesheets
  .agents/             # AI agent configuration
  LICENSE              # License file
  README.md            # This file
```
{frontend_section}
## Development

1. Edit `templates/{name}/index_partial.html` to build your UI
2. Add view logic in `views.py`
3. Add styles in `static/{name}/css/{name}.css`
4. Run tests: `python -m django test {name}`

## Standalone and hosted verification

Install this package with its `scitex` extra to obtain the SDK GUI runtime.
Run the app's GUI launcher locally and verify the same URL/view module under
a host plugin mount. The `scitex.apps` entry point names this app's config;
the host handles registration without importing app domain code directly.

Validate before publication: `scitex-sdk app validate {name}`.
Verify host deployment capabilities before claiming an installation is live.

## License

{label} is licensed under {license_id} — see `LICENSE` for details.
"""


# EOF
