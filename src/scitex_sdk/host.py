"""Host capabilities consumed by leaf GUIs in standalone and mounted modes.

The host owns authorization and credentials. Leaves own schema, computation,
views and rendering. Providers are trusted host settings, never request input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID


class AccessError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)


class CapabilityUnavailable(Exception):
    """The host has not supplied the requested authorized capability."""


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
    if mode == "hub" and not getattr(
        getattr(request, "user", None), "is_authenticated", False
    ):
        raise AccessError("Authentication required", 401)
    resolution = project_context.resolve_active_project(request, remember=remember)
    if resolution.state == project_context.STATE_UNAVAILABLE:
        raise CapabilityUnavailable("Project provider is unavailable")
    if not resolution.ok:
        raise AccessError("Project not available", 404)
    storage = _provider("SCITEX_PROJECT_STORAGE")
    project = resolution.project
    root = storage.project_path(project.id, request)
    if root is None:
        raise AccessError("Project workspace not found", 404)
    can_write = storage.can_write(project.id, request) is True
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


__all__ = [
    "AccessError",
    "CapabilityUnavailable",
    "ProjectAccess",
    "StoreAccess",
    "authenticated_user",
    "project_access",
    "store_access",
]
