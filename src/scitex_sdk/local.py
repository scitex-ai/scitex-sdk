"""Single-user standalone providers for the same leaf capability contract."""

from pathlib import Path
from uuid import UUID

from scitex_sdk.host import CapabilityUnavailable, StoreAccess
from scitex_sdk.ui import project_scope


def _root():
    from django.conf import settings

    return Path(settings.SCITEX_LOCAL_PROJECT_ROOT).resolve()


class LocalProjectProvider(project_scope.LocalProjectProvider):
    def __init__(self):
        super().__init__(_root())


class LocalProjectStorage:
    def project_path(self, project_id, request):
        root = _root()
        path = (root / project_id).resolve()
        if path.parent != root or not path.is_dir() or path.name.startswith("."):
            return None
        return str(path)

    def can_write(self, project_id, request):
        return self.project_path(project_id, request) is not None


class LocalProjectStore:
    def store_access(self, project_id, request):
        from django.conf import settings

        if LocalProjectStorage().project_path(project_id, request) is None:
            raise CapabilityUnavailable("Project not available")
        entry = getattr(settings, "SCITEX_LOCAL_PROJECT_STORES", {}).get(project_id)
        if not entry:
            raise CapabilityUnavailable(
                "Private store is not configured for this project"
            )
        try:
            return StoreAccess(
                tenant_id=UUID(entry["tenant_id"]),
                dsn=entry["dsn"],
                project_scope=entry["project_scope"],
                owner_role=entry["owner_role"],
            )
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise CapabilityUnavailable(
                "Private store configuration is invalid"
            ) from exc
