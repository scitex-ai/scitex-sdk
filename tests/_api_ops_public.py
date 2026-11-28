"""A leaf with one public read (API-A004), served through the real SDK host path."""

from scitex_sdk.app.api_exec import ApiPage
from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import ApiPluginRef
from scitex_sdk.app.api_serve import api_urlpatterns

OPERATIONS = (
    ApiOperation(
        "catalog",
        "entries",
        "list",
        f"{__name__}:list_entries",
        summary="Public catalogue entries",
        paginated=True,
        public=True,
    ),
)
PLUGIN = build_plugin("catalog", "Catalog API", "1", OPERATIONS)


def list_entries(call):
    rows = [{"id": "e1"}, {"id": "e2"}]
    return ApiPage(rows[call.offset : call.offset + call.limit], has_more=False)


REF = ApiPluginRef(name="catalog", target=f"{__name__}:PLUGIN", distribution="")
urlpatterns = api_urlpatterns([REF])
