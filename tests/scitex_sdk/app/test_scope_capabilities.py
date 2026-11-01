"""The optional manifest declaration is operational, not storage tenancy."""
import pytest
from scitex_sdk.app._app_scope import normalize_scope_capabilities


@pytest.mark.parametrize("user,project", [(True, True), (True, False), (False, True), (False, False)])
def test_explicit_capability_pairs_are_preserved(user, project):
    # Arrange
    declared = {"user": user, "project": project}
    # Act
    result = normalize_scope_capabilities(declared)
    # Assert
    assert result == declared


@pytest.mark.parametrize("value", [{}, {"user": True}, {"user": "true", "project": False},
                                  {"user": 1, "project": False}, {"user": True, "project": True, "scope": "project"}])
def test_malformed_capabilities_fail_loudly(value):
    # Arrange
    # Act / Assert
    with pytest.raises(ValueError, match="explicit user/project booleans"):
        normalize_scope_capabilities(value)


def test_omitted_declaration_makes_no_support_claim():
    # Arrange
    # Act
    result = normalize_scope_capabilities(None)
    # Assert
    assert result is None


def test_generated_starter_declares_actual_user_workspace_support():
    # Arrange
    import json
    from scitex_sdk.app.appmaker._scaffold_html import _manifest_json
    # Act
    manifest = json.loads(_manifest_json("sample", "Sample", "fas fa-star", "", None, "MIT"))
    # Assert
    assert manifest["scope_capabilities"] == {"user": True, "project": False}


def test_manifest_validator_rejects_invalid_scope_capabilities(tmp_path):
    # Arrange
    from scitex_sdk.app.appmaker._validate._manifest import validate_manifest
    (tmp_path / "manifest.json").write_text('{"scope_capabilities":{"user":"true","project":false}}')
    # Act
    errors = validate_manifest(tmp_path)
    # Assert
    assert any("scope_capabilities requires explicit" in error for error in errors)


def test_public_embed_exports_the_existing_normalizer():
    # Arrange
    from scitex_sdk.app.embed import normalize_scope_capabilities as public_normalizer
    # Act
    result = public_normalizer is normalize_scope_capabilities
    # Assert
    assert result
