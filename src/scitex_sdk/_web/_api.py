"""The SDK's own API, declared as contract operations (served at /api/v1/sdk/)."""

from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiError

OPERATIONS = (
    ApiOperation(
        "sdk",
        "skills",
        "list",
        "scitex_sdk._web._handlers:list_skills",
        summary="Skills bundled with the installed scitex-sdk (ids only, no paths)",
        errors=(
            ApiError(
                "sdk.skills_unavailable", 503, "Bundled skills are unavailable", True
            ),
        ),
        paginated=True,
        default_limit=100,
        max_limit=200,
        public=True,
    ),
)

plugin = build_plugin("sdk", "SciTeX SDK", "1", OPERATIONS)
