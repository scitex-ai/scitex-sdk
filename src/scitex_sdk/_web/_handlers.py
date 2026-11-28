"""Handlers of the SDK's own operations (see :mod:`._api`)."""

from scitex_sdk._bundled_skills import list_bundled_skills
from scitex_sdk.app.api_exec import ApiPage, ApiProblem


def list_skills(call):
    """Bundled skill ids, one row per skill: never user/home paths."""
    try:
        groups = list_bundled_skills()
    except (OSError, ValueError, RuntimeError):
        raise ApiProblem(
            503,
            "sdk.skills_unavailable",
            "bundled skills are unavailable",
            retryable=True,
        ) from None
    rows = [
        {"id": f"{namespace}/{skill}", "namespace": namespace, "skill_id": skill}
        for namespace in sorted(groups)
        for skill in groups[namespace]
    ]
    page = rows[call.offset : call.offset + call.limit]
    return ApiPage(page, has_more=call.offset + len(page) < len(rows), total=len(rows))
