"""Public operations (API-A004), trailing-slash hints (API-R004) and the audit rule."""

from pathlib import Path

from django.test import Client, override_settings

from scitex_sdk.app._api_contract import scan_api_contract
from scitex_sdk.app.api_ops import ApiOperation
from scitex_sdk.app.api_rules import ApiContractViolation
from scitex_sdk.testing.api_contract import run_contract_suite
from tests._api_ops_public import PLUGIN

HOOKS = dict(
    ROOT_URLCONF="tests._api_ops_public",
    SCITEX_API_CALLER="scitex_sdk.testing.api_contract.contract_caller",
)


def _get(path, token=None):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    with override_settings(**HOOKS):
        return Client().get(path, **headers)


def test_a_public_read_answers_without_a_credential():
    # Arrange
    path = "/api/v1/catalog/entries"
    # Act
    response = _get(path)
    # Assert
    assert [row["id"] for row in response.json()["data"]] == ["e1", "e2"]


def test_an_invalid_bearer_on_a_public_read_is_still_a_401():
    # Arrange
    path = "/api/v1/catalog/entries"
    # Act
    response = _get(path, token="not-a-token")
    # Assert
    assert response.status_code == 401


def test_a_trailing_slash_names_the_canonical_path():
    # Arrange
    path = "/api/v1/catalog/entries/"
    # Act
    response = _get(path)
    # Assert
    assert "try /api/v1/catalog/entries" in response.json()["detail"]


def test_a_public_write_is_refused_at_declaration():
    # Arrange
    kwargs = dict(public=True)
    # Act
    try:
        ApiOperation("catalog", "entries", "create", "m:f", **kwargs)
        rule = None
    except ApiContractViolation as exc:
        rule = exc.rule
    # Assert
    assert rule == "API-A004"


def test_the_contract_suite_accepts_a_public_leaf():
    # Arrange
    target = "tests._api_ops_public:PLUGIN"
    # Act
    found = run_contract_suite(PLUGIN, target=target)
    # Assert
    assert found == []


def test_the_audit_reports_a_hand_written_plugin_as_api_d001(tmp_path: Path):
    # Arrange
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "api.py").write_text(
        "from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit\n"
        "PLUGIN = ApiPlugin(id='legacy', title='Legacy', api_version='1', routes=(\n"
        "    ApiRoute(path='ping', methods=('GET',), rate=RateLimit('standard', 'light'),\n"
        "             auth=AuthScope(public=True, project_scope='none'),\n"
        "             handler='pkg.api:ping', read_only=True),))\n"
        "def ping(request):\n    return None\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "legacy"\nversion = "1"\n'
        '[project.entry-points."scitex.apis"]\nlegacy = "pkg.api:PLUGIN"\n'
    )
    # Act
    findings = scan_api_contract(tmp_path)
    # Assert
    assert [f.detail.split("]")[0] for f in findings] == ["legacy: [API-D001"]
