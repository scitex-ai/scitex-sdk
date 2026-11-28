"""The aggregate: per-package listings composed, live evidence reconciled."""

from scitex_sdk.app.api_inventory import PackageSpec, aggregate
from scitex_sdk.app.api_inventory._aggregate import clusters, reconcile_live_auth

NOTES = PackageSpec(
    "scitex-notes", import_name="tests", mcp_server="tests._api_inventory_mcp:mcp"
)


def _row(auth, behaviour, token_behaviour=None):
    live = {"behaviour": behaviour}
    if token_behaviour:
        live["with_token"] = {"behaviour": token_behaviour}
    return {
        "kind": "rest",
        "path": "/api/x/",
        "methods": ["GET"],
        "auth": list(auth),
        "live": live,
    }


def test_a_refused_anonymous_get_overrides_a_static_none():
    # Arrange
    row = _row(["none"], "unauthorized")
    # Act
    reconcile_live_auth(row)
    # Assert
    assert row["auth"] == ["gated-in-body"]


def test_an_open_anonymous_get_keeps_none():
    # Arrange
    row = _row(["none"], "open")
    # Act
    reconcile_live_auth(row)
    # Assert
    assert row["auth"] == ["none"]


def test_a_token_that_opens_a_gated_endpoint_is_recorded():
    # Arrange
    row = _row(["session"], "login-redirect", token_behaviour="open")
    # Act
    reconcile_live_auth(row)
    # Assert
    assert row["auth"] == ["probe-token", "session"]


def test_the_document_counts_every_entry_once():
    # Arrange
    doc = aggregate([NOTES])
    # Act
    total = doc["totals"]["entries"]
    # Assert
    assert total == len(doc["entries"])


def test_clusters_group_violations_by_owner_and_prefix():
    # Arrange
    entries = [
        {
            "kind": "rest",
            "path": "/api/stats/calculate/",
            "owner_package": "scitex-hub",
            "violations": ["API-R001"],
        },
        {
            "kind": "rest",
            "path": "/api/stats/describe/",
            "owner_package": "scitex-hub",
            "violations": ["API-R001", "API-A004"],
        },
    ]
    # Act
    found = clusters(entries)
    # Assert
    assert (found[0]["prefix"], found[0]["count"], found[0]["rules"]) == (
        "/api/stats",
        2,
        {"API-R001": 2, "API-A004": 1},
    )
