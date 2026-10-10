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
An optional ``canonical_project_id(request, selector)`` maps a legacy selector
to a listed canonical ID. SDK always checks the returned ID against this
request's access list before remembering or returning it.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, cast, runtime_checkable

__all__ = [
    "PROJECT_PROVIDER_META_NAME",
    "PROJECT_PROVIDER_SETTING",
    "PROJECT_PROVIDER_URL_SETTING",
    "PROJECT_QUERY_PARAM",
    "LocalProjectProvider",
    "ProjectEntry",
    "ProjectProvider",
    "ProjectSelection",
    "ScopedProjectProvider",
    "canonical_project_selector",
    "host_project_provider",
    "host_project_provider_url",
    "project_id_for",
    "project_listing_view",
    "resolve_project",
    "scoped_project_listing_view",
    "supports_scoped_capability",
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


def canonical_project_selector(
    request: Any, provider: ProjectProvider, selector: str, accessible: Collection[str]
) -> str | None:
    """Return only a listed ID, optionally using a host's selector alias.

    Canonical IDs retain their existing behavior. Alias normalization is an
    optional host capability, never an authorization grant or a fallback to
    the stored project. Both the original and normalized IDs are checked
    against the current request's access list.
    """
    if not isinstance(selector, str) or not selector:
        return None
    if selector in accessible:
        return selector
    normalize = getattr(provider, "canonical_project_id", None)
    if normalize is None:
        return None
    canonical = normalize(request, selector)
    return canonical if isinstance(canonical, str) and canonical in accessible else None


def resolve_project(
    request: Any, provider: ProjectProvider, explicit: Optional[str] = None
) -> Optional[str]:
    """The project id the app should open; see the module docstring for precedence."""
    accessible = {entry.id for entry in provider.list_projects(request)}
    if explicit:
        selected = canonical_project_selector(request, provider, explicit, accessible)
        if selected is None:
            return None
        provider.remember(request, selected)
        return selected
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
            (
                p
                for p in self.root.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ),
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
        if request.method == "GET":
            chosen = resolve_provider(request)
            entries = chosen.list_projects(request)
            return JsonResponse(
                {
                    "projects": [entry.as_option() for entry in entries],
                    "current": resolve_project(request, chosen),
                }
            )
        if request.method == "POST":
            try:
                payload = json.loads(request.body or b"{}")
                project_id = payload.get("id") if isinstance(payload, dict) else None
            except ValueError:
                project_id = None
            # POST always requests an explicit selection. Invalid input must
            # not become navigation's absent-selector fallback to stored state.
            if not isinstance(project_id, str) or not project_id:
                return JsonResponse({"error": "project not accessible"}, status=403)
            chosen = resolve_provider(request)
            selected = resolve_project(request, chosen, explicit=project_id)
            if selected is None:
                return JsonResponse({"error": "project not accessible"}, status=403)
            return JsonResponse({"current": selected})
        return HttpResponseNotAllowed(["GET", "POST"])

    return view


@dataclass(frozen=True)
class ProjectSelection:
    """One authorized tagged selection: explicit user scope or a project.

    ``{"scope": "user", "id": None}`` is the explicit All selection;
    ``{"scope": "project", "id": <canonical id>}`` is a project selection.
    Anything else (unknown scope, user-with-id, empty project id) is refused
    at construction. ``None`` (no selection) is represented by the absence
    of a pair, never by a null scope — the wire contract omits
    ``current_scope`` for unselected state.
    """

    scope: str
    id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.scope == "user":
            if self.id is not None:
                raise ValueError("a user selection carries no project id")
        elif self.scope == "project":
            if not isinstance(self.id, str) or not self.id:
                raise ValueError("a project selection needs a nonempty id")
        else:
            raise ValueError(f"unknown selection scope: {self.scope!r}")


@runtime_checkable
class ScopedProjectProvider(Protocol):
    """Optional tagged-scope capability for a project provider.

    Detected separately via :func:`supports_scoped_capability`; never added
    to :class:`ProjectProvider`, whose three methods and legacy
    ``remember(project_id)`` stay the only required surface. The provider
    owns one committed scope/ID pair plus its legacy project projection and
    persists them atomically; the SDK never writes scope and project apart.
    """

    def current_scope(self, request: Any) -> Optional[ProjectSelection]:
        """The committed tagged selection, or None when unselected."""

    def remember_scope(self, request: Any, selection: ProjectSelection) -> None:
        """Atomically commit one authorized tagged selection."""


def supports_scoped_capability(provider: Any) -> bool:
    """Whether ``provider`` offers the optional tagged-scope capability."""
    return isinstance(provider, ScopedProjectProvider)


def _tagged_selection(payload: Any) -> ProjectSelection:
    """Build the requested tagged selection, refusing anything else.

    The explicit pair shape is enforced: ``user`` requires the ``id`` key
    present with a literal null; ``project`` requires a nonempty string id.
    A missing key is not an explicit null — it is refused like any other
    malformed selection.
    """
    if not isinstance(payload, dict):
        raise ValueError("selection must be an object")
    scope = payload.get("scope")
    if scope == "user":
        if "id" not in payload or payload["id"] is not None:
            raise ValueError("a user selection needs an explicit null id")
        return ProjectSelection(scope="user", id=None)
    if scope == "project":
        return ProjectSelection(scope="project", id=payload.get("id"))
    raise ValueError("unknown selection scope")


def scoped_project_listing_view(
    provider: ProjectProvider | Callable[[Any], ProjectProvider],
) -> Callable:
    """A Django view serving the picker's HTTP contract plus tagged scope.

    Default-off: the tagged ``{scope, id}`` payload is accepted only when
    the resolved provider offers :class:`ScopedProjectProvider`; otherwise
    only the legacy ``POST {id}`` shape works, byte-for-byte compatible with
    :func:`project_listing_view` (same shapes, same 403s). ``GET`` adds
    ``allow_user_scope`` (true only for a supporting provider) plus
    ``current_scope`` for a committed tagged selection, omitted when
    unselected. Stale, unknown, or null scopes are never accepted as
    All; an explicit user selection requires the provider's support.
    ``provider`` may be a factory taking the request.
    """
    from django.http import HttpResponseNotAllowed, JsonResponse

    def resolve_provider(request: Any) -> ProjectProvider:
        return provider if isinstance(provider, ProjectProvider) else provider(request)

    def view(request: Any):
        if request.method == "GET":
            chosen = resolve_provider(request)
            entries = chosen.list_projects(request)
            scoped = supports_scoped_capability(chosen)
            body: dict = {
                "projects": [entry.as_option() for entry in entries],
                "current": resolve_project(request, chosen),
                "allow_user_scope": scoped,
            }
            if scoped:
                selection = cast(ScopedProjectProvider, chosen).current_scope(request)
                valid = isinstance(selection, ProjectSelection) and (
                    (selection.scope == "user" and selection.id is None)
                    or (
                        selection.scope == "project"
                        and isinstance(selection.id, str)
                        and selection.id
                        and selection.id
                        in {entry.id for entry in entries}
                    )
                )
                if valid:
                    assert isinstance(selection, ProjectSelection)
                    body["current_scope"] = selection.scope
                    body["current"] = selection.id
                else:
                    # Unselected is always {current: null} with current_scope
                    # omitted: a stale legacy projection must never stand in
                    # for an explicit tagged selection.
                    body["current"] = None
            return JsonResponse(body)
        if request.method == "POST":
            try:
                payload = json.loads(request.body or b"{}")
            except ValueError:
                payload = None
            if isinstance(payload, dict) and "scope" not in payload:
                project_id = payload.get("id")
                if not isinstance(project_id, str) or not project_id:
                    return JsonResponse(
                        {"error": "project not accessible"}, status=403
                    )
                chosen = resolve_provider(request)
                selected = resolve_project(request, chosen, explicit=project_id)
                if selected is None:
                    return JsonResponse(
                        {"error": "project not accessible"}, status=403
                    )
                return JsonResponse({"current": selected})
            try:
                selection = _tagged_selection(payload)
            except ValueError:
                return JsonResponse(
                    {"error": "project not accessible"}, status=403
                )
            chosen = resolve_provider(request)
            if not supports_scoped_capability(chosen):
                return JsonResponse(
                    {"error": "project not accessible"}, status=403
                )
            scoped = cast(ScopedProjectProvider, chosen)
            if selection.scope == "user":
                scoped.remember_scope(request, selection)
                return JsonResponse({"current": None, "current_scope": "user"})
            accessible = {entry.id for entry in chosen.list_projects(request)}
            selected = canonical_project_selector(
                request, chosen, selection.id or "", accessible
            )
            if selected is None:
                return JsonResponse(
                    {"error": "project not accessible"}, status=403
                )
            committed = ProjectSelection(scope="project", id=selected)
            scoped.remember_scope(request, committed)
            return JsonResponse({"current": selected, "current_scope": "project"})
        return HttpResponseNotAllowed(["GET", "POST"])

    return view


# EOF
