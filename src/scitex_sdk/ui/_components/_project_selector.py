#!/usr/bin/env python3
"""Project selector component metadata."""

from .._registry import register_component


class ProjectSelector:
    """The SDK project picker (compass L625).

    A dropdown with fuzzy search that lists the projects the user can access,
    shows the current selection on the trigger, and emits
    ``stx-project-selector:change`` (bubbles, detail ``{id, name}``).

    A project-scope app places it in its own UI, never the global header:
    ``{% load scitex_project_picker %}{% scitex_project_picker provider_url=... %}``
    renders nothing for user-scope apps. The list comes from a
    ``ProjectProvider`` (``scitex_sdk.ui.project_scope`` on the server,
    ``httpProjectProvider`` in TS), so the component knows nothing about
    permissions. Keyboard: arrows, Enter, Escape; 44px targets on touch.

    CSS: scitex_sdk/ui/css/app/project-selector.css
    """

    name = "project-selector"
    version = "0.2.0"
    description = (
        "Project picker with fuzzy search over a provider's accessible "
        "projects; emits stx-project-selector:change"
    )
    ts_entry = "scitex_sdk/ui/ts/app/project-selector/index"
    css_file = "scitex_sdk/ui/css/app/project-selector.css"
    # Pre-built ES-module sibling for consumers without a bundler step:
    # a browser executes the .js module directly where it cannot execute
    # the .ts. Mirrors the TS API (same exports). Rebuild command is in
    # the file banner.
    js_file = "scitex_sdk/ui/js/app/project-selector.js"


register_component(ProjectSelector.name, ProjectSelector)
