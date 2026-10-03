# File: scitex_sdk/app/project_context/__init__.py

"""Leaf project context, using the SDK UI provider protocol.

The host supplies the projects an authenticated user may access. This module
returns explicit ok, none, denied and unavailable states, plus a display-safe
project descriptor and the stable scitex.project.change command.

An explicit project wins over last visited, then nothing is selected. A denied
explicit project never falls back; unavailable providers never invent a
workspace. App and UI implementations ship in the same SDK distribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "CHANGE_PROJECT_COMMAND",
    "PROJECT_QUERY_PARAM",
    "STANDALONE_PROVIDER_PATH",
    "STATE_DENIED",
    "STATE_NONE",
    "STATE_OK",
    "STATE_UNAVAILABLE",
    "VALID_STATES",
    "ActiveProject",
    "ProjectDeniedError",
    "ProjectResolution",
    "ProjectUnavailableError",
    "change_project",
    "project_context",
    "project_provider_endpoint",
    "resolve_active_project",
]

#: The query parameter carrying an explicit project, agreed with SDK UI
#: (``scitex_sdk.ui.project_scope.PROJECT_QUERY_PARAM``). An explicit project wins
#: over the stored one — that is the route/query half of persistence.
PROJECT_QUERY_PARAM = "project"

#: The stable command name for changing the active project.
#:
#: STABLE AND NAMED, not a URL and not a method name, because every input
#: modality has to reach the same operation: a mouse click, a touch, a keyboard
#: binding, a recorded macro, and an agent all address this one identity. A
#: command spelled as a URL breaks the moment the mount prefix changes, and one
#: spelled as a Python function name is unreachable from the browser.
CHANGE_PROJECT_COMMAND = "scitex.project.change"

#: Declared resolution states. Nothing else is ever set.
#:
#: ``ok``          a project is selected and the user may access it.
#: ``none``        nothing selected (or the stored project is gone). The app
#:                 shows its picker. THIS IS NOT AN ERROR.
#: ``denied``      an explicit project was asked for and is not accessible.
#: ``unavailable`` no provider is configured, so no project CAN be resolved.
STATE_OK = "ok"
STATE_NONE = "none"
STATE_DENIED = "denied"
STATE_UNAVAILABLE = "unavailable"
VALID_STATES = (STATE_OK, STATE_NONE, STATE_DENIED, STATE_UNAVAILABLE)


@runtime_checkable
class _ProjectProvider(Protocol):
    """Structural subset of the SDK UI project-provider protocol.

    App and UI share one distribution. This module accepts an injected
    provider without importing Django or configuring a host; the structural
    contract is checked against ``scitex_sdk.ui.project_scope.ProjectProvider``.
    """

    def list_projects(self, request: Any) -> list:
        """Projects this request's user can access, in display order."""
        ...

    def last_visited(self, request: Any) -> str | None:
        """The stored last visited project id, or None."""
        ...

    def remember(self, request: Any, project_id: str) -> None:
        """Store ``project_id`` as the last visited project."""
        ...


@dataclass(frozen=True)
class ActiveProject:
    """A project as a LEAF APP is allowed to see it.

    TWO FIELDS, and the omission is the point. SDK UI's ``ProjectEntry``
    also carries ``detail``, which ``LocalProjectProvider`` fills with the
    project's filesystem path. That field is provider-internal: rendering it
    puts an internal path in front of a user, which the product rules forbid
    ("never internal ``MASTER/`` paths"). A descriptor with no path field
    cannot leak one, so this is structural rather than a rule someone has to
    remember.

    ``name`` is the user-facing label. A provider that returns an empty name
    falls back to the id — never to a path, and never to an invented label.
    """

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("ActiveProject requires a non-empty id")
        if not self.name:
            raise ValueError(
                "ActiveProject requires a non-empty name; a project with no "
                "user-facing label must not reach a display slot"
            )

    def as_dict(self) -> dict:
        """The JSON-safe shape for templates and the browser."""
        return {"id": self.id, "name": self.name}


@dataclass(frozen=True)
class ProjectResolution:
    """One shape for every outcome, so a caller never guesses which keys exist.

    Mirrors ``scitex_sdk.app._gui_runtime.PortHolder``: the state is a declared
    constant, and the invariants below make an inconsistent resolution
    impossible to construct rather than merely unlikely to be written.
    """

    state: str
    project: ActiveProject | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"unknown project state: {self.state!r}")
        if self.state == STATE_OK and self.project is None:
            raise ValueError("state='ok' requires a project")
        if self.state != STATE_OK and self.project is not None:
            raise ValueError(
                f"state={self.state!r} must not carry a project — a resolution "
                "that is not 'ok' has no active project to hand over"
            )

    @property
    def ok(self) -> bool:
        """True only when a project was resolved."""
        return self.state == STATE_OK


class ProjectDeniedError(PermissionError):
    """An explicit project was requested that this user may not access.

    An EXCEPTION rather than a falsy return, because the caller wrote a command
    whose entire meaning is "make this project active". Silently leaving the
    old project selected would look like success while the UI said otherwise —
    and the fail-closed rule requires the request be REFUSED, not downgraded.
    """


class ProjectUnavailableError(RuntimeError):
    """No project context could be computed, so no command could be applied.

    DISTINCT FROM :class:`ProjectDeniedError` on purpose. "You may not" and "we
    could not ask" call for different responses — one is a permission answer,
    the other is an outage — and collapsing them would tell a user they lack
    access to something that was never checked.
    """


#: Where the standalone launcher registers its provider.
#:
#: A dotted path, because that is the channel SDK UI reads
#: (``settings.SCITEX_PROJECT_PROVIDER``), so a standalone app resolves its
#: project through the SAME code path a hosted app does. The name is public so
#: the launcher and any consumer can agree on it without a second constant.
STANDALONE_PROVIDER_PATH = "scitex_sdk.app.project_context.StandaloneProjectProvider"


def _host_provider() -> tuple[_ProjectProvider | None, str]:
    """Resolve the registered SDK provider without guessing a project.

    Django and the host provider are optional runtime capabilities. A missing
    or invalid provider yields an unavailable state rather than local access.
    """
    try:
        from scitex_sdk.ui.project_scope import host_project_provider
    except ImportError:
        return None, "SDK UI could not be imported, so no provider can be resolved"
    try:
        provider = host_project_provider()
    except Exception as exc:  # noqa: BLE001 - host provider boundary is untrusted
        return None, f"the configured provider could not be loaded: {exc}"
    if provider is None:
        reason = (
            "no project provider is configured "
            "(settings.SCITEX_PROJECT_PROVIDER is empty)"
        )
        return None, reason
    return provider, ""


def _accessible(provider: _ProjectProvider, request: Any) -> dict[str, ActiveProject]:
    """Every project ``request``'s user may access, keyed by id.

    A provider entry without an id, or with an empty name, is SKIPPED rather
    than repaired: inventing a label or an id for it would put a made-up
    project in a picker.
    """
    found: dict[str, ActiveProject] = {}
    for entry in provider.list_projects(request):
        entry_id = getattr(entry, "id", "") or ""
        if not entry_id:
            continue
        name = getattr(entry, "name", "") or entry_id
        found[entry_id] = ActiveProject(id=entry_id, name=name)
    return found


def resolve_active_project(
    request: Any,
    provider: _ProjectProvider | None = None,
    explicit: str | None = None,
    *,
    remember: bool = True,
) -> ProjectResolution:
    """Resolve the project this request should open, fail-closed.

    Precedence, identical to ``scitex_sdk.ui.project_scope.resolve_project``
    because it is the same rule and not a second one:

    1. An ``explicit`` project (argument, else ``?project=``) wins. If the user
       may not access it, the result is ``denied`` — it NEVER falls back to the
       stored project, because the caller asked for a different one and
       silently substituting another is the failure this rule exists to stop.
    2. Otherwise the stored last-visited project, if it is still accessible.
    3. Otherwise ``none``: the app shows its picker. Nothing is auto-selected,
       and no example project is ever created or chosen on a user's behalf.

    Navigation remembers an authorized explicit selection by default. Resource
    requests use ``remember=False`` so late work for an earlier project cannot
    overwrite a newer selection. Both modes apply the same access checks.
    """
    resolved_provider = provider
    if resolved_provider is None:
        resolved_provider, reason = _host_provider()
        if resolved_provider is None:
            return ProjectResolution(state=STATE_UNAVAILABLE, reason=reason)

    if explicit is None:
        explicit = _explicit_from_request(request)

    try:
        accessible = _accessible(resolved_provider, request)
    except Exception as exc:  # noqa: BLE001 - provider implementations are external
        # Fail CLOSED, not loudly-500. A provider that cannot answer must not
        # make the page unrenderable, and it must never be read as "no project"
        # (which would show an empty picker as if the user had none) or as "ok".
        # `unavailable` is the declared state for exactly this, and the reason
        # travels with it so the cause is readable rather than merely absent.
        return ProjectResolution(
            state=STATE_UNAVAILABLE,
            reason=f"the project provider failed to list projects: {exc}",
        )

    if explicit:
        try:
            from scitex_sdk.ui.project_scope import canonical_project_selector

            selected = canonical_project_selector(
                request, resolved_provider, explicit, accessible
            )
        except Exception as exc:  # noqa: BLE001 - host provider boundary
            return ProjectResolution(
                state=STATE_UNAVAILABLE,
                reason=f"the project provider failed to normalize the selection: {exc}",
            )
        if selected is None:
            return ProjectResolution(
                state=STATE_DENIED,
                reason=(
                    f"project {explicit!r} is not accessible to this user. "
                    "Refused rather than falling back: the requested project "
                    "either does not exist or belongs to someone else, and a "
                    "distinction is not disclosed because telling them apart "
                    "would confirm another user's project exists."
                ),
            )
        explicit = selected
        # An explicit project BECOMES the stored one. This is the persistence
        # half of the rule: a link carrying ?project=foo has to survive the
        # next navigation, or "selected once and carried across every leaf app"
        # holds only for as long as the query string is on the URL. Written
        # AFTER the access check, so a refused project is never persisted.
        if remember:
            try:
                resolved_provider.remember(request, explicit)
            except Exception as exc:  # noqa: BLE001 - persistence provider is external
                return ProjectResolution(
                    state=STATE_UNAVAILABLE,
                    reason=(
                        "the project provider failed to store the selected "
                        f"project: {exc}"
                    ),
                )
        return ProjectResolution(state=STATE_OK, project=accessible[explicit])

    try:
        stored = resolved_provider.last_visited(request)
    except Exception as exc:  # noqa: BLE001 - provider implementations are external
        return ProjectResolution(
            state=STATE_UNAVAILABLE,
            reason=f"the project provider failed to report the stored project: {exc}",
        )
    if stored and stored in accessible:
        return ProjectResolution(state=STATE_OK, project=accessible[stored])

    return ProjectResolution(
        state=STATE_NONE,
        reason=(
            "no project is selected (or the stored one is no longer "
            "accessible); the app shows its picker"
        ),
    )


def _explicit_from_request(request: Any) -> str | None:
    """``?project=`` from the request, or None. Any request shape is tolerated.

    A request without ``GET`` is legitimate here — this function is also called
    from view code that resolved the project from a URL path instead, where the
    caller passes ``explicit`` itself.
    """
    get = getattr(request, "GET", None)
    if get is None:
        return None
    try:
        value = get.get(PROJECT_QUERY_PARAM)
    except Exception:  # noqa: BLE001 - tolerate non-QueryDict request adapters
        return None
    return value or None


def project_context(
    request: Any,
    provider: _ProjectProvider | None = None,
    *,
    remember: bool = True,
) -> dict:
    """Context processor: hand every leaf template its project context.

    Register once and a mounted app renders its project surface without the
    view having to pass anything::

        TEMPLATES[0]["OPTIONS"]["context_processors"] += [
            "scitex_sdk.app.project_context.project_context",
        ]

    The COMMAND NAME travels with the context on purpose. The picker's change
    action is addressed by identity (``project_command``), not by a URL the
    template would have to build — so the shell, a keyboard binding, a recorded
    macro and an agent all invoke the same operation, and none of them breaks
    when the mount prefix changes.

    Keys: ``active_project`` (dict or None), ``project_state`` (a declared
    state), ``project_command``.

    By default an authorized explicit navigation is remembered, preserving
    the existing context-processor contract. Use ``remember=False`` for a
    read-only render when the view already owns navigation persistence.
    """
    resolution = resolve_active_project(request, provider, remember=remember)
    return {
        "active_project": (
            resolution.project.as_dict() if resolution.project else None
        ),
        "project_state": resolution.state,
        "project_command": CHANGE_PROJECT_COMMAND,
        # The slot travels with the context too: a leaf that renders a picker
        # affordance needs to know WHERE to fetch the list from, and the answer
        # is the host's, not something the leaf may construct.
        "project_provider_endpoint": project_provider_endpoint(),
    }


def change_project(
    request: Any, project_id: str, provider: _ProjectProvider | None = None
) -> ActiveProject:
    """The ``scitex.project.change`` command: make ``project_id`` the active one.

    THE ONE OPERATION every input modality addresses. It is named rather than
    bound to a route so a click, a keystroke, a macro and an agent are all
    calling this and not four implementations of it.

    Fails closed in both directions, and changes NOTHING when it refuses:

    * an unknown or unauthorised id raises :class:`ProjectDeniedError`, and the
      previously stored project is left untouched — a refused command must not
      half-apply;
    * a provider that cannot answer raises :class:`ProjectUnavailableError`,
      which is NOT the same answer as "you may not";
    * an empty id raises ``ValueError``: there is no such thing as changing to
      "no project", and accepting one would clear the user's selection by
      accident.
    """
    if not project_id:
        raise ValueError(
            "change_project requires a project id; an empty id would clear the "
            "user's selection rather than change it"
        )

    resolved_provider = provider
    if resolved_provider is None:
        resolved_provider, reason = _host_provider()
        if resolved_provider is None:
            raise ProjectUnavailableError(f"cannot change project: {reason}")

    try:
        accessible = _accessible(resolved_provider, request)
    except Exception as exc:
        raise ProjectUnavailableError(
            f"cannot change project: the provider failed to list projects: {exc}"
        ) from exc

    if project_id not in accessible:
        raise ProjectDeniedError(
            f"project {project_id!r} is not accessible to this user; the "
            "active project is unchanged"
        )

    try:
        resolved_provider.remember(request, project_id)
    except Exception as exc:
        raise ProjectUnavailableError(
            "cannot change project: the provider failed to store the selected "
            f"project: {exc}"
        ) from exc
    return accessible[project_id]


def project_provider_endpoint() -> str:
    """Return the host-declared picker URL, or an empty unavailable slot.

    SDK UI owns ``SCITEX_PROJECT_PROVIDER_URL`` and its URL resolution. This
    request-independent helper delegates to that owner; authentication remains
    the responsibility of the leaf rendering the picker. The UI template tag
    uses the same resolver and additionally requires a signed-in visitor.
    """
    try:
        from scitex_sdk.ui.project_scope import host_project_provider_url
    except ImportError:
        return ""
    try:
        return host_project_provider_url() or ""
    except Exception:  # noqa: BLE001 - broken host reverse must not take down leaf
        # A broken reverse() must not take down a leaf page whose only
        # job here was to advertise a slot.
        return ""


def _standalone_provider_class():
    """Bind the SDK local provider to the launcher's owned working directory.

    Host settings instantiate providers without arguments, so the class reads
    ``SCITEX_WORKING_DIR`` supplied by the standalone launcher. Construction
    selects nothing: the picker remains empty until an explicit selection.
    The UI provider import stays lazy to keep pure project contracts independent
    of Django configuration.
    """
    import os

    try:
        from scitex_sdk.ui.project_scope import LocalProjectProvider
    except ImportError as exc:
        raise ImportError(
            "StandaloneProjectProvider needs the SDK UI capability: "
            "pip install scitex-sdk[gui]"
        ) from exc

    class StandaloneProjectProvider(LocalProjectProvider):
        """Every non-hidden folder under the standalone working directory."""

        def __init__(self) -> None:
            super().__init__(root=os.environ.get("SCITEX_WORKING_DIR") or os.getcwd())

    return StandaloneProjectProvider


def __getattr__(name: str):
    """Resolve the provider lazily at the public host-setting dotted path."""
    if name == "StandaloneProjectProvider":
        return _standalone_provider_class()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# EOF
