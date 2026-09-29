#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SciTeX App Creator — the appmaker scaffolding wizard as a web UI.

Served from the SDK via ``scitex-sdk gui serve`` (see
:mod:`scitex_sdk.cli`), mounted by hosts (scitex-hub) as a generic
Django app through :mod:`scitex_sdk.creator.urls`.

The appmaker ENGINE (scaffold, validate, publish, dev-install) still
lives in ``scitex-app`` and is imported from there — per the facade
pattern, the implementation consolidates into the SDK gradually. This
package owns what is NEW: the starter cards, the wizard views, and the
standalone-server adapter.

Starters are not separate scaffolds. Each one is a short brief layered
over the same html template: it lands in the manifest's ``ai_hint`` and
in an extra AGENTS.md section, so the app-maker agent knows what to
build first. The SDK owns these definitions so scitex-hub's create page
and this wizard cannot drift apart (the hub should import from here).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Starter:
    """One card on the create page.

    brief is the internal build instruction for the agent. creates and
    builds_first are the plain-language card copy: what gets created
    and what the agent builds first.
    """

    key: str
    label: str
    hint: str
    icon: str
    brief: str
    creates: str = ""
    builds_first: str = ""


STARTERS: tuple[Starter, ...] = (
    Starter(
        "data_entry",
        "Data entry form",
        "Record trials, samples or observations into the project.",
        "fas fa-table-list",
        "Build a data entry form for one experiment. Each submission appends a "
        "row to a CSV file under the project's data/ directory. Validate "
        "required fields and show the latest rows under the form.",
        creates=(
            "A private app project with a data-entry form scaffold: an input "
            "form, required-field validation, answers saved as CSV rows under "
            "the project's data/ folder, and the latest rows shown under the "
            "form."
        ),
        builds_first=(
            "A form for one experiment. Each submission appends a row to a "
            "CSV file under data/, with validation and recent rows visible."
        ),
    ),
    Starter(
        "dashboard",
        "Analysis dashboard",
        "Summarise and plot result files from the project.",
        "fas fa-chart-line",
        "Build an analysis dashboard. List CSV result files in the project, "
        "let the user pick one, and show summary statistics and a simple plot.",
        creates=(
            "A private app project with an analysis-dashboard scaffold: a "
            "result-file picker, summary statistics, and a simple plot of the "
            "selected CSV file."
        ),
        builds_first=(
            "A dashboard that lists CSV result files in the project and shows "
            "summary statistics plus a plot for the chosen file."
        ),
    ),
    Starter(
        "log_viewer",
        "Device/log viewer",
        "Browse and filter instrument logs or recordings.",
        "fas fa-wave-square",
        "Build a device/log viewer. List log or recording files in the project, "
        "open one, and let the user scroll, search and filter its lines or "
        "samples by time.",
        creates=(
            "A private app project with a log-viewer scaffold: a file list to "
            "open one log or recording, then scroll, search, and filter its "
            "lines or samples by time."
        ),
        builds_first=(
            "A viewer that lists log or recording files, opens one, and lets "
            "you scroll, search, and filter by time."
        ),
    ),
    Starter(
        "blank",
        "Blank",
        "Start from the plain template and describe it to the agent.",
        "fas fa-puzzle-piece",
        "Start from the plain template; build what the description asks for.",
        creates=(
            "A private app project with the plain template only — no "
            "pre-built feature. The agent builds whatever your description "
            "asks for."
        ),
        builds_first=(
            "Whatever your description above asks for, starting from the "
            "plain template."
        ),
    ),
)

STARTERS_BY_KEY = {s.key: s for s in STARTERS}

DEFAULT_STARTER = "blank"

#: Longest label the wizard accepts. scitex-hub truncates project
#: descriptions at 500 chars and project names at 90; the label becomes
#: a directory slug, so it shares the 90-char budget.
MAX_LABEL_LENGTH = 90


def app_module_name(slug: str) -> str:
    """Derive a scaffold module name from a label slug.

    Twin of scitex-hub's ``app_create.app_module_name`` so local
    creates and hub creates produce the same module name for the same
    label. ``init_app`` requires the ``_app`` suffix.
    """
    name = re.sub(r"[^a-z0-9_]", "_", slug.lower()).strip("_") or "my"
    if name[0].isdigit():
        name = f"app_{name}"
    return name if name.endswith("_app") else f"{name}_app"


def target_slug(label: str) -> str:
    """Derive a directory slug from a label (hub ``_project_name`` twin)."""
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", label.strip().lower()).strip("-._")
    return name[:90] or "my-app"


def validate_create_input(
    label: str, description: str, starter_key: str
) -> list[str]:
    """Validate wizard input without touching the filesystem.

    Pure so the JSON API and the tests share one implementation.
    Returns error strings (empty = valid).
    """
    _ = description  # free text; length is capped at the hub, not here.
    errors = []
    if not (label or "").strip():
        errors.append("Give your app a name.")
    elif len(label.strip()) > MAX_LABEL_LENGTH:
        errors.append(f"Keep the name under {MAX_LABEL_LENGTH} characters.")
    if starter_key not in STARTERS_BY_KEY:
        errors.append("Pick a starter template.")
    return errors


def starter_brief_section(starter: Starter, description: str) -> str:
    """AGENTS.md section recording what the user asked for (hub twin)."""
    return (
        "\n\n## What the user asked for\n\n"
        f"Starter: **{starter.label}**\n\n"
        f"{starter.brief}\n\n"
        f"User's description: {description or '(none yet — ask them)'}\n"
    )


__all__ = [
    "DEFAULT_STARTER",
    "MAX_LABEL_LENGTH",
    "STARTERS",
    "STARTERS_BY_KEY",
    "Starter",
    "app_module_name",
    "starter_brief_section",
    "target_slug",
    "validate_create_input",
]

# EOF
