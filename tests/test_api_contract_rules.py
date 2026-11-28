"""Declaration-time refusals name their API contract rule (API-* ids)."""

import pytest

from scitex_sdk.app.api_ops import ApiOperation, build_plugin
from scitex_sdk.app.api_plugin import (
    ApiError,
    ApiField,
    ApiPluginContractError,
    ApiSchema,
)
from scitex_sdk.app.api_rules import RULES, ApiContractViolation

H = "tests._api_ops_leaf:get_note"
CASES = [
    (dict(resource="Notes"), "API-R002"),
    (dict(resource="note"), "API-R003"),
    (dict(package="mcp"), "API-R006"),
    (dict(verb="get", item=False), "API-V001"),
    (dict(verb="archive"), "API-V002"),
    (dict(read_only=True), "API-V004"),
    (dict(paginated=True), "API-G001"),
    (dict(verb="list", paginated=True, default_limit=50, max_limit=500), "API-G001"),
    (dict(params=(ApiField("pageSize", "integer", False),)), "API-F001"),
    (dict(params=(ApiField("format", "string", False, enum=("JSON",)),)), "API-F001"),
    (dict(errors=(ApiError("NotFound", 404, "missing"),)), "API-E002"),
    (dict(errors=(ApiError("other.not_found", 404, "missing"),)), "API-E002"),
    (
        dict(verb="archive", item=True, response=ApiSchema("Job", (ApiField("id"),))),
        "API-J001",
    ),
    (dict(compute_cost="huge"), "API-K001"),
    (dict(rate_class="turbo"), "API-H002"),
    (dict(handler="not a handler"), "API-D006"),
]


def _refusal(**kwargs):
    base = dict(package="notes", resource="notes", verb="get", handler=H)
    base.update(kwargs)
    try:
        ApiOperation(**base)
    except ApiContractViolation as exc:
        return exc
    return None


def _plugin_refusal(*args, **kwargs):
    try:
        build_plugin(*args, **kwargs)
    except ApiContractViolation as exc:
        return exc
    return None


@pytest.mark.parametrize("kwargs, rule", CASES)
def test_each_declaration_rule_refuses_with_its_id(kwargs, rule):
    # Arrange
    expected_prefix = f"[{rule}] "
    # Act
    refusal = _refusal(**kwargs)
    # Assert
    assert (refusal.rule, str(refusal).startswith(expected_prefix)) == (rule, True)


def test_a_refusal_is_still_a_contract_error_for_existing_handlers():
    # Arrange
    kwargs = dict(resource="note")
    # Act
    refusal = _refusal(**kwargs)
    # Assert
    assert isinstance(refusal, ApiPluginContractError)


def test_a_refusal_names_the_operation():
    # Arrange
    kwargs = dict(resource="data", verb="list")
    # Act
    refusal = _refusal(**kwargs)
    # Assert
    assert str(refusal) == (
        "[API-R003] notes.data.list: resource 'data' must be a plural noun"
    )


def test_a_sort_enum_may_carry_a_descending_sign():
    # Arrange
    sort = ApiField("sort", "string", False, enum=("created_at", "-created_at"))
    # Act
    op = ApiOperation("notes", "notes", "list", H, params=(sort,), paginated=True)
    # Assert
    assert op.paginated is True


def test_an_unsupported_contract_major_is_refused():
    # Arrange
    op = ApiOperation("notes", "notes", "get", H)
    # Act
    refusal = _plugin_refusal("notes", "Notes", "1", (op,), contract="2")
    # Assert
    assert refusal.rule == "API-D003"


def test_a_reserved_package_cannot_build_a_plugin():
    # Arrange
    reserved = "health"
    # Act
    refusal = _plugin_refusal(reserved, "Health", "1", ())
    # Assert
    assert refusal.rule == "API-R006"


def test_a_duplicate_operation_is_refused_as_a_tool_name_clash():
    # Arrange
    op = ApiOperation("notes", "notes", "get", H)
    # Act
    refusal = _plugin_refusal("notes", "Notes", "1", (op, op))
    # Assert
    assert refusal.rule == "API-T001"


def test_every_rule_id_used_is_registered():
    # Arrange
    ids = {rule for _kwargs, rule in CASES} | {"API-D003", "API-T001"}
    # Act
    missing = ids - set(RULES)
    # Assert
    assert missing == set()
