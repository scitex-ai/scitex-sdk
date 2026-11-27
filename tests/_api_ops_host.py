"""A host for the API serving tests: caller, limiter, meter, urls — real objects."""

from types import SimpleNamespace

from scitex_sdk.app.api_exec import ApiCaller, ApiProblem
from scitex_sdk.app.api_plugin import ApiPluginRef
from scitex_sdk.app.api_serve import InMemoryIdempotencyStore, api_urlpatterns

#: token -> scopes
TOKENS = {"read-token": ("notes:*:read",), "write-token": ("notes:*:write",)}
METERED = []
LIMITED = {"on": False}
STORE = InMemoryIdempotencyStore()

REF = ApiPluginRef(
    name="notes", target="tests._api_ops_leaf:PLUGIN", distribution="scitex-notes"
)


def caller(request):
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip()
    if token not in TOKENS:
        return None
    user = SimpleNamespace(username="alice", pk="alice", is_authenticated=True)
    return ApiCaller(user=user, scopes=TOKENS[token], via="token", token_id=token)


class Limiter:
    def check(self, caller, operation, request):
        if LIMITED["on"]:
            raise ApiProblem(
                429, "api.rate_limited", "slow down", headers={"Retry-After": "7"}
            )


class Meter:
    def record(self, event):
        METERED.append(event)


urlpatterns = api_urlpatterns([REF])
