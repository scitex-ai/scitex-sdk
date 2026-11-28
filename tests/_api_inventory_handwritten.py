"""A hand-written (not operation-built) plugin, as leaves declared them before v1."""

from scitex_sdk.app.api_plugin import ApiPlugin, ApiPluginRef, ApiRoute, AuthScope, RateLimit

PLUGIN = ApiPlugin(
    id="legacy",
    title="Legacy",
    api_version="1",
    routes=(
        ApiRoute(
            path="skills",
            methods=("GET",),
            rate=RateLimit(rate_class="free", compute_cost="low"),
            auth=AuthScope(public=True, project_scope="none"),
            handler="tests._api_inventory_handwritten:skills",
            read_only=True,
        ),
    ),
)
REF = ApiPluginRef(
    name="legacy", target="tests._api_inventory_handwritten:PLUGIN", distribution="scitex-legacy"
)


def skills(call):
    return {}
