"""Optional-Django adapter over the SDK's package-only skill catalog."""

from scitex_sdk._bundled_skills import list_bundled_skills


def bundled_skills(request):
    """Serialize bundled names, never user/home paths or ambient skill stores."""
    try:
        from django.http import JsonResponse
    except ImportError as exc:
        raise ImportError("SDK Web responses require scitex-sdk[gui].") from exc

    if request.method != "GET":
        response = JsonResponse(
            {
                "error": {
                    "code": "method_not_allowed",
                    "message": "Use GET for the bundled skills catalog.",
                }
            },
            status=405,
        )
        response["Allow"] = "GET"
        return response
    try:
        skills = list_bundled_skills()
    except (OSError, ValueError, RuntimeError):
        return JsonResponse(
            {
                "error": {
                    "code": "bundled_skills_unavailable",
                    "message": "Bundled SDK skill resources are unavailable.",
                }
            },
            status=503,
        )
    return JsonResponse({"package": "scitex-sdk", "skills": skills})
