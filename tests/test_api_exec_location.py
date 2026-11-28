"""API-V001: a 201 create carries Location (the item URL of the new object)."""

from scitex_sdk.app.api_exec import ApiCaller, execute
from scitex_sdk.app.api_ops import ApiOperation

_CREATE = ApiOperation("leaf", "items", "create", "leafpkg.api:create")
_CALLER = ApiCaller(user=None, scopes=("*",))


def test_a_create_answers_201_with_the_item_location():
    # Arrange
    def handler(call):
        return {"id": "org~name", "created_at": "2026-11-29T00:00:00Z"}

    # Act
    result = execute(_CREATE, _CALLER, {}, handler=handler)
    # Assert
    assert (result.status, result.headers.get("Location")) == (
        201,
        "/api/v1/leaf/items/org~name",
    )


def test_a_create_without_an_id_has_no_location():
    # Arrange
    def handler(call):
        return {"name": "x"}

    # Act
    result = execute(_CREATE, _CALLER, {}, handler=handler)
    # Assert
    assert (result.status, "Location" in result.headers) == (201, False)
