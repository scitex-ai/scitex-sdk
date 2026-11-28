"""A Django host serving hosted MCP over the notes and catalog test leaves.

Real objects only: a bearer-token authenticator (the REST caller contract),
a meter, a limiter and a project resolver over a local directory, exactly
what a host supplies.
"""

from pathlib import Path
from types import SimpleNamespace

from scitex_sdk.app.api_exec import ApiCaller, ApiProblem
from scitex_sdk.app.api_mcp_http import HostedMcp, McpHooks, mcp_urlpattern
from scitex_sdk.app.api_serve import InMemoryIdempotencyStore
from tests._api_ops_leaf import PLUGIN as NOTES
from tests._api_ops_public import PLUGIN as CATALOG

#: token -> (scopes, tier, project restriction)
TOKENS = {
    "read-token": (("notes:*:read",), "member", None),
    "write-token": (("notes:*:write",), "member", None),
    "paid-token": (("notes:*:write",), "paid", None),
    "project-token": (("notes:notes:write",), "member", "alice/notes"),
    "catalog-only": (("catalog:*:read",), "member", None),
}
METERED = []
LIMITED = {"on": False}
STORE = InMemoryIdempotencyStore()
PROJECT_ROOTS = {}  # "owner/slug" -> directory; filled by the test fixture


def caller(request):
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip()
    if token not in TOKENS:
        return None
    scopes, tier, project = TOKENS[token]
    user = SimpleNamespace(username="alice", pk="alice", is_authenticated=True)
    return ApiCaller(
        user=user,
        scopes=scopes,
        via="token",
        token_id=token,
        project=project,
        tier=tier,
    )


class Limiter:
    def check(self, caller, operation, request):
        if LIMITED["on"]:
            raise ApiProblem(
                429, "api.rate_limited", "slow down", headers={"Retry-After": "7"}
            )


class Meter:
    def record(self, event):
        METERED.append(event)


def project_resolver(request):
    def resolve(caller, project_id, write):
        from scitex_sdk.host import AccessError, ProjectAccess

        root = PROJECT_ROOTS.get(project_id)
        if root is None:
            raise AccessError("Project not available", 404)
        return ProjectAccess(project_id, Path(root).name, Path(root), can_write=write)

    return resolve


#: Hooks read from Django settings (the Hub's path): SCITEX_API_CALLER etc.
SETTINGS_ENDPOINT = HostedMcp(
    [NOTES, CATALOG], tool_tiers={"notes.notes.archive": "paid"}
)
#: Credential-less callers allowed; they see the public catalogue only.
OPEN_ENDPOINT = HostedMcp([NOTES, CATALOG], anonymous=True)
#: Explicit hooks (any host), including project authorization.
EXPLICIT_HOOKS = McpHooks(
    authenticate=caller,
    project_resolver=project_resolver,
    rate_limiter=Limiter(),
    meter=Meter(),
    idempotency_store=STORE,
)

urlpatterns = [
    mcp_urlpattern(endpoint=SETTINGS_ENDPOINT),
    mcp_urlpattern("api/v1/mcp-open", endpoint=OPEN_ENDPOINT),
    mcp_urlpattern(
        "api/v1/mcp-explicit",
        endpoint=HostedMcp([NOTES], resource_metadata_url="https://h.example/prm"),
        hooks=EXPLICIT_HOOKS,
    ),
]
