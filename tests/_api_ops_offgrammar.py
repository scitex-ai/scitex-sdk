"""A hand-written plugin whose route is NOT an SDK operation (refused by hosts)."""

from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit

PLUGIN = ApiPlugin(
    id="legacy",
    title="Hand-written legacy API",
    api_version="1",
    routes=(
        ApiRoute(
            path="ping",
            methods=("GET",),
            rate=RateLimit(rate_class="standard", compute_cost="light"),
            auth=AuthScope(public=True, project_scope="none"),
            handler="tests._api_ops_offgrammar:ping",
            read_only=True,
        ),
    ),
)


def ping(request):
    return None
