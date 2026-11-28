"""A small real host URLconf for the API-inventory tests.

Each view is an ordinary Django view written the way hub views are written
(decorators, mixins, inline checks), plus the generic contract mount of the
``notes`` test leaf.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from scitex_sdk.app.api_serve import api_urlpatterns
from tests._api_ops_host import REF


@login_required
@require_POST
def create_project(request):
    return JsonResponse({"ok": True})


@csrf_exempt
def open_hook(request):
    if request.method == "POST":
        return JsonResponse({"ok": True})
    return JsonResponse({}, status=405)


@user_passes_test(lambda u: u.is_superuser)
@require_http_methods(["GET", "DELETE"])
def admin_tool(request, pk):
    return JsonResponse({"pk": pk})


def public_status(request):
    return JsonResponse({"status": "ok"})


def inline_checked(request):
    if not request.user.is_authenticated:
        return JsonResponse({}, status=401)
    return JsonResponse({})


class Dashboard(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({})


def home(request):
    return JsonResponse({})


nested = [
    path("tools/<int:pk>/", admin_tool, name="admin-tool"),
    re_path(r"^status/$", public_status, name="status"),
]

urlpatterns = [
    path("", home, name="home"),
    path("api/project/create/", create_project, name="project-create"),
    path("api/hooks/open/", open_hook, name="open-hook"),
    path("api/me/check/", inline_checked, name="me-check"),
    path("apps/dash/api/summary/", Dashboard.as_view(), name="dash-summary"),
    path("api/", include(nested)),
    path("apps/demo/<path:endpoint>", public_status, name="demo-dispatch"),
    *api_urlpatterns([REF]),
]
