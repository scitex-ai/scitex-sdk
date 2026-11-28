"""A leaf with public-tier candidates, and the host pieces that serve it.

``calc.sums.run`` is a read-only action (``public_eligible``), ``calc.renders.create``
is a write (``public_eligible``, needs a key in the tier), ``calc.notes.create``
keeps the default ``member`` ceiling.
"""

from types import SimpleNamespace

from scitex_sdk.app.api_exec import ApiCaller
from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiField, ApiPluginRef
from scitex_sdk.app.api_serve import api_urlpatterns

VALUES = ApiField("values", "array", True, "Numbers to add")
OPERATIONS = (
    ApiOperation(
        "calc",
        "sums",
        "run",
        f"{__name__}:run_sum",
        summary="Add numbers",
        item=False,
        read_only=True,
        params=(VALUES,),
        exposure="public_eligible",
    ),
    ApiOperation(
        "calc",
        "renders",
        "create",
        f"{__name__}:create_render",
        summary="Render something",
        params=(VALUES,),
        exposure="public_eligible",
    ),
    ApiOperation(
        "calc",
        "notes",
        "create",
        f"{__name__}:create_note",
        summary="Write a note",
        params=(VALUES,),
    ),
)
PLUGIN = build_plugin("calc", "Calc API", "1", OPERATIONS)
SEEN = []


def run_sum(call):
    SEEN.append(call)
    limits = call.limits
    if limits is not None and len(call.params["values"]) > limits.max_values:
        from scitex_sdk.app.api_exec import ApiProblem

        raise ApiProblem(413, "calc.too_many_values", "too many values")
    return {"total": sum(call.params["values"]), "class": call.priority_class}


def create_render(call):
    SEEN.append(call)
    return {"id": "r1"}


def create_note(call):
    SEEN.append(call)
    return {"id": "n1"}


TOKENS = {
    "member-key": ("*",),
    "paid-key": ("*",),
}
METERED = []


def caller(request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token not in TOKENS:
        return None
    user = SimpleNamespace(username=token, pk=token, is_authenticated=True)
    tier = "paid" if token == "paid-key" else "member"
    return ApiCaller(
        user=user, scopes=TOKENS[token], via="token", token_id=token, tier=tier
    )


class Meter:
    def record(self, event):
        METERED.append(event)


class Admission:
    calls = []

    def admit(self, decision, op, caller, request):
        Admission.calls.append((decision.priority_class, op.operation_id))


TIER = {
    "calc.sums.run": {"public": True, "limits": "stats-inline"},
    "calc.renders.create": {"public": True, "limits": "light", "requires": "key"},
    "calc.notes.create": {"public": True, "limits": "light"},
}
REF = ApiPluginRef(name="calc", target=f"{__name__}:PLUGIN", distribution="")
urlpatterns = api_urlpatterns([REF])
