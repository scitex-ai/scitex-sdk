#!/usr/bin/env python3
"""Project scope for SDK apps: which projects a picker offers, and which one is current.

A project-scope app (manifest ``"scope": "project"``) asks a provider for the
projects the user can access and for the user's last visited project. The
provider is the host's: the hub serves owned plus shared projects from its
database, a standalone app lists local project folders
(:class:`LocalProjectProvider`). Nothing here checks permissions itself.

The precedence the SDK guarantees, in :func:`resolve_project`:

1. An explicit project (URL path or ``?project=``) always wins, and becomes the
   new last visited project. An explicit project the user cannot access
   resolves to ``None``; it never falls back to the stored one.
2. Without one, the last visited project, if the user can still access it.
3. Otherwise ``None``; the app shows its picker.

The host registers its provider as a host service, so a leaf app places the
picker without knowing who serves the projects::

    SCITEX_PROJECT_PROVIDER = "myhost.projects.HostProjectProvider"  # dotted path
    SCITEX_PROJECT_PROVIDER_URL = "api_project_scope"  # URL name or path

:func:`host_project_provider` and :func:`host_project_provider_url` read them;
``{% scitex_project_provider_meta %}`` advertises the URL to client code
(``hostProjectProvider()`` in TS). A provider may also define
``project_id(project) -> str`` so a template can pass its project object.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, runtime_checkable

__all__ = [
    "PROJECT_PROVIDER_META_NAME",
    "PROJECT_PROVIDER_SETTING",
    "PROJECT_PROVIDER_URL_SETTING",
    "PROJECT_QUERY_PARAM",
    "LocalProjectProvider",
    "ProjectEntry",
    "ProjectProvider",
    "host_project_provider",
    "host_project_provider_url",
    "project_id_for",
    "project_listing_view",
    "resolve_project",
]

PROJECT_QUERY_PARAM = "project"
PROJECT_PROVIDER_SETTING = "SCITEX_PROJECT_PROVIDER"
PROJECT_PROVIDER_URL_SETTING = "SCITEX_PROJECT_PROVIDER_URL"
PROJECT_PROVIDER_META_NAME = "stx-project-provider"


@dataclass(frozen=True)
class ProjectEntry:
    """One pickable project; ``as_option`` is the TS ``ProjectOption`` shape."""

    id: str
    name: str
    detail: str = ""

    def as_option(self) -> dict:
        option = asdict(self)
        if not self.detail:
            option.pop("detail")
        return option


@runtime_checkable
class ProjectProvider(Protocol):
    def list_projects(self, request: Any) -> list[ProjectEntry]:
        """Projects this request's user can access, in display order."""

    def last_visited(self, request: Any) -> Optional[str]:
        """The stored last visited project id, or None."""

    def remember(self, request: Any, project_id: str) -> None:
        """Store ``project_id`` as the last visited project."""


def resolve_project(
    request: Any, provider: ProjectProvider, explicit: Optional[str] = None
) -> Optional[str]:
    """The project id the app should open; see the module docstring for precedence."""
    accessible = {entry.id for entry in provider.list_projects(request)}
    if explicit:
        if explicit not in accessible:
            return None
        provider.remember(request, explicit)
        return explicit
    stored = provider.last_visited(request)
    return stored if stored in accessible else None


class LocalProjectProvider:
    """Standalone provider: every non-hidden folder under ``root`` is a project."""

    def __init__(self, root: Path | str, state_file: Path | str | None = None):
        self.root = Path(root)
        self.state_file = (
            Path(state_file)
            if state_file
            else self.root / ".scitex" / "last_project.json"
        )

    def list_projects(self, request: Any = None) -> list[ProjectEntry]:
        if not self.root.is_dir():
            return []
        folders = sorted(
            (p for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")),
            key=lambda p: p.name.lower(),
        )
        return [ProjectEntry(id=p.name, name=p.name, detail=str(p)) for p in folders]

    def last_visited(self, request: Any = None) -> Optional[str]:
        try:
            return json.loads(self.state_file.read_text("utf-8")).get("project")
        except (OSError, ValueError, AttributeError):
            return None

    def remember(self, request: Any, project_id: str) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"project": project_id}), "utf-8")


def host_project_provider() -> Optional[ProjectProvider]:
    """The host's registered provider (``settings.SCITEX_PROJECT_PROVIDER``), or None."""
    from django.conf import settings
    from django.utils.module_loading import import_string

    dotted = getattr(settings, PROJECT_PROVIDER_SETTING, "")
    if not dotted:
        return None
    provider = import_string(dotted)
    return provider() if isinstance(provider, type) else provider


def host_project_provider_url() -> str:
    """The host provider's HTTP endpoint (``settings.SCITEX_PROJECT_PROVIDER_URL``), or ""."""
    from django.conf import settings
    from django.urls import NoReverseMatch, reverse

    target = getattr(settings, PROJECT_PROVIDER_URL_SETTING, "")
    if not target or "/" in target:
        return target or ""
    try:
        return reverse(target)
    except NoReverseMatch:
        return ""


def project_id_for(project: Any, provider: Optional[ProjectProvider] = None) -> str:
    """A project's picker id: strings pass through; objects go through ``provider.project_id``."""
    if not project:
        return ""
    if isinstance(project, str):
        return project
    to_id = getattr(provider or host_project_provider(), "project_id", None)
    return to_id(project) if to_id else str(project)


def project_listing_view(
    provider: ProjectProvider | Callable[[Any], ProjectProvider],
) -> Callable:
    """A Django view serving the picker's HTTP provider contract.

    ``GET`` returns ``{"projects": [...], "current": <last visited or null>}``;
    ``POST {"id": ...}`` remembers an accessible project (403 otherwise).
    ``provider`` may be a factory taking the request.
    """
    from django.http import HttpResponseNotAllowed, JsonResponse

    def resolve_provider(request: Any) -> ProjectProvider:
        return provider if isinstance(provider, ProjectProvider) else provider(request)

    def view(request: Any):
        chosen = resolve_provider(request)
        if request.method == "GET":
            entries = chosen.list_projects(request)
            return JsonResponse(
                {
                    "projects": [entry.as_option() for entry in entries],
                    "current": resolve_project(request, chosen),
                }
            )
        if request.method == "POST":
            try:
                project_id = json.loads(request.body or b"{}").get("id")
            except (ValueError, AttributeError):
                project_id = None
            if resolve_project(request, chosen, explicit=project_id) is None:
                return JsonResponse({"error": "project not accessible"}, status=403)
            return JsonResponse({"current": project_id})
        return HttpResponseNotAllowed(["GET", "POST"])

    return view


# EOF
