"""Host capabilities consumed by leaf GUIs in standalone and mounted modes.

The host owns authorization and credentials. Leaves own schema, computation,
views and rendering. Providers are trusted host settings, never request input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import UUID


class AccessError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)


class CapabilityUnavailable(Exception):
    """The host has not supplied the requested authorized capability."""


class StorageRefused(AccessError):
    """The host's storage quota or spend controls refuse a write.

    ``status`` is 402 (spend controls) or 413 (quota); ``code`` is the host's
    machine-readable reason and ``link`` where the user can act on it (raise a
    cap, free space). A leaf shows ``str(exc)`` and ``link``; it never retries
    around the refusal.
    """

    def __init__(
        self,
        message: str,
        status: int = 402,
        *,
        code: str = "",
        link: Optional[str] = None,
    ):
        super().__init__(message, status)
        self.code = code
        self.link = link


@dataclass(frozen=True)
class StorageBudget:
    """What the host reports about the storage behind one project.

    Every field is optional: a host states what it knows and leaves the rest
    ``None`` ("not reported"), which is different from zero. ``spend_level``
    is the host's own word for the account's standing (for example ``ok``,
    ``warning``, ``blocked``).
    """

    used_bytes: Optional[int] = None
    quota_bytes: Optional[int] = None
    max_file_bytes: Optional[int] = None
    spend_level: Optional[str] = None
    spend_percent: Optional[float] = None
    link: Optional[str] = None

    @property
    def remaining_bytes(self) -> Optional[int]:
        if self.used_bytes is None or self.quota_bytes is None:
            return None
        return max(0, self.quota_bytes - self.used_bytes)


@dataclass(frozen=True)
class ProjectAccess:
    id: str
    name: str
    root: Path = field(repr=False)
    can_write: bool = False

    def path(self, relative: str) -> Path:
        root = self.root.resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise AccessError("File must be inside this project")
        return path


@dataclass(frozen=True)
class StoreAccess:
    tenant_id: UUID
    dsn: str = field(repr=False)
    project_scope: str
    owner_role: str


def _provider(setting):
    from django.conf import settings
    from django.utils.module_loading import import_string

    value = getattr(settings, setting, None)
    if not value:
        raise CapabilityUnavailable("Host capability is not configured")
    provider = import_string(value) if isinstance(value, str) else value
    return provider() if isinstance(provider, type) else provider


def authenticated_user(request):
    """Session identity or the host's explicitly registered API authenticator."""
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return user
    from django.conf import settings

    if not getattr(settings, "SCITEX_API_AUTHENTICATOR", None):
        return None
    return _provider("SCITEX_API_AUTHENTICATOR")(request)


def project_access(
    request, *, write: bool = False, remember: bool = True
) -> ProjectAccess:
    """Authorize a workspace; resource reads may leave navigation unchanged.

    ``remember=False`` resolves explicit projects with the same authorization
    and write checks without storing a new active-project selection.
    """
    from django.conf import settings

    from scitex_sdk.app import project_context

    mode = getattr(settings, "SCITEX_APP_MODE", "hub")
    if mode not in {"hub", "standalone"}:
        raise CapabilityUnavailable("Host mode is invalid")
    if mode == "hub":
        user = authenticated_user(request)
        if not getattr(user, "is_authenticated", False):
            raise AccessError("Authentication required", 401)
        # The host alone authenticates credentials. Bind its identity to this
        # request so project, storage and store providers authorize the same user.
        request.user = user
    resolution = project_context.resolve_active_project(request, remember=remember)
    if resolution.state == project_context.STATE_UNAVAILABLE:
        raise CapabilityUnavailable("Project provider is unavailable")
    if not resolution.ok:
        raise AccessError("Project not available", 404)
    storage = _provider("SCITEX_PROJECT_STORAGE")
    project = resolution.project

    def _can_write() -> bool:
        # A missing or raising permission check is a qualified capability
        # failure, never a bare 500, and a non-explicit-True grant is a
        # refusal, not an absent value.
        try:
            return storage.can_write(project.id, request) is True
        except Exception as exc:
            raise CapabilityUnavailable(
                "Write permission check unavailable"
            ) from exc

    if write:
        # Authorization precedes resolution: a write request without an
        # explicit-True can_write is refused before any project path is
        # resolved, so path resolution can never precede the write grant.
        # The grant is validated again after resolution: the provider owns
        # atomicity, but the SDK must not issue a capability the provider
        # no longer grants. Read, 401, 404, and provider-unavailable
        # behavior are unchanged.
        if not _can_write():
            raise AccessError("Write access required", 403)
    root = storage.project_path(project.id, request)
    if root is None:
        raise AccessError("Project workspace not found", 404)
    can_write = _can_write()
    if write and not can_write:
        raise AccessError("Write access required", 403)
    return ProjectAccess(project.id, project.name, Path(root).resolve(), can_write)


def store_access(request, project_id: str) -> StoreAccess:
    """Private store configuration for an authorized project; no ambient fallback."""
    capability = _provider("SCITEX_PROJECT_STORE").store_access(project_id, request)
    if not isinstance(capability, StoreAccess):
        raise CapabilityUnavailable("Private store configuration is invalid")
    if not isinstance(capability.tenant_id, UUID) or not capability.tenant_id.int:
        raise CapabilityUnavailable("Private store configuration is invalid")
    if not all((capability.dsn, capability.project_scope, capability.owner_role)):
        raise CapabilityUnavailable("Private store configuration is invalid")
    return capability


def _storage_gate():
    return _provider("SCITEX_STORAGE_GATE")


def storage_budget(request, project: ProjectAccess) -> StorageBudget:
    """The host's storage/spend report for an AUTHORIZED project.

    Read-only. The host decides whose account backs the project (owner,
    organization). Raises :class:`CapabilityUnavailable` when the host does
    not supply ``SCITEX_STORAGE_GATE`` or its answer is malformed.
    """
    if not isinstance(project, ProjectAccess):
        raise TypeError("storage_budget needs the ProjectAccess from project_access")
    try:
        budget = _storage_gate().budget(project.id, request)
    except CapabilityUnavailable:
        raise
    except Exception as exc:
        raise CapabilityUnavailable("Storage budget is unavailable") from exc
    if not isinstance(budget, StorageBudget):
        raise CapabilityUnavailable("Storage budget is invalid")
    return budget


def require_storage_write(
    request, project: ProjectAccess, *, incoming_sizes: Sequence[int]
) -> None:
    """Ask the host whether ``incoming_sizes`` bytes may be written to ``project``.

    Call it BEFORE writing (or queuing a job that writes). Returns ``None`` when
    allowed; raises :class:`StorageRefused` when the quota or spend controls
    refuse, :class:`AccessError` 403 without write access, and
    :class:`CapabilityUnavailable` when the host has no gate — a leaf must then
    not write, because "nobody checked" is not "allowed".
    """
    if not isinstance(project, ProjectAccess):
        raise TypeError(
            "require_storage_write needs the ProjectAccess from project_access"
        )
    if not project.can_write:
        raise AccessError("Write access required", 403)
    sizes = [int(size) for size in incoming_sizes]
    if any(size < 0 for size in sizes):
        raise ValueError("incoming sizes must be non-negative")
    gate = _storage_gate()
    try:
        gate.require_storage_write(project.id, request, incoming_sizes=sizes)
    except (StorageRefused, CapabilityUnavailable):
        raise
    except AccessError:
        raise
    except Exception as exc:
        raise CapabilityUnavailable("Storage gate is unavailable") from exc


__all__ = [
    "AccessError",
    "CapabilityUnavailable",
    "ProjectAccess",
    "StorageBudget",
    "StorageRefused",
    "StoreAccess",
    "authenticated_user",
    "project_access",
    "require_storage_write",
    "storage_budget",
    "store_access",
]
