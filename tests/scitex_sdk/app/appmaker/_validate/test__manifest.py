"""Tests for scitex_sdk/app/appmaker/_validate/_manifest.py."""

from __future__ import annotations

import json

from scitex_sdk.app.appmaker._validate import (
    validate_manifest,
    validate_manifest_advisory,
    MANIFEST_REQUIRED_KEYS,
)
from ._helpers import (
    write_manifest,
)


# ---------------------------------------------------------------------------
# Tests: validate_manifest
# ---------------------------------------------------------------------------


class TestValidateManifest:
    def test_missing_manifest_returns_error(self, tmp_path):
        # Arrange
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("not found" in e for e in errors)

    def test_invalid_json_returns_error(self, tmp_path):
        # Arrange
        (tmp_path / "manifest.json").write_text("{bad json}", encoding="utf-8")
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("not valid JSON" in e for e in errors)

    def test_non_object_manifest_returns_error(self, tmp_path):
        # Arrange
        (tmp_path / "manifest.json").write_text("[1, 2, 3]", encoding="utf-8")
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("must be a JSON object" in e for e in errors)

    def test_missing_required_keys_adds_errors(self, tmp_path):
        # Arrange
        (tmp_path / "manifest.json").write_text(json.dumps({"name": "myapp"}))
        # Act
        errors = validate_manifest(tmp_path)
        # All keys other than "name" should trigger errors
        # Assert
        assert len(errors) > 0

    def test_all_required_keys_present(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "my_app"
        data["slug"] = "my-app"
        data["label"] = "My App"
        data["icon"] = "fas fa-star"
        data["license"] = "MIT"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert errors == []

    # --- mobile_layout (tristate: absent=no claim / false=desktop-only / true) ---

    def test_mobile_layout_true_is_valid(self, tmp_path):
        # Arrange
        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mobile_layout"] = True
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert — a declared phone layout is valid.
        assert errors == []

    def test_mobile_layout_false_is_valid(self, tmp_path):
        # Arrange
        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mobile_layout"] = False
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert — an explicit desktop-only claim is valid.
        assert errors == []

    def test_omitted_mobile_layout_is_valid(self, tmp_path):
        # Arrange — no claim; the hub falls back to its existing metadata.
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert — absence is the safe default, not an error.
        assert errors == []

    def test_non_bool_mobile_layout_is_rejected(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mobile_layout"] = "yes"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert — a typo must fail loud here, naming the field.
        assert any("mobile_layout" in e for e in errors)

    def test_name_without_app_suffix_is_not_an_error(self, tmp_path):
        """The suffix convention is advice; enforcing it made it unclearable."""
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "mybadname"  # no _app suffix
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert not [e for e in errors if "_app" in e or "-app" in e]

    def test_name_without_app_suffix_is_an_advisory(self, tmp_path):
        """The other arm: moved to the warn tier, NOT deleted.

        Without this, the assertion above would also pass if the finding had
        simply been dropped -- which is the failure a "stop enforcing it" change
        most resembles.
        """
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "mybadname"
        write_manifest(tmp_path, data)
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert any("_app" in w or "-app" in w for w in warnings)

    def test_name_with_app_suffix_raises_no_advisory(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "my_app"
        data["label"] = "SciTeX Test App"
        write_manifest(tmp_path, data)
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert warnings == []

    def test_advisory_on_a_missing_manifest_is_silent(self, tmp_path):
        """validate_manifest() already reports this, as an error; not twice."""
        # Arrange — tmp_path holds no manifest.json
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert warnings == []

    def test_advisory_on_unparseable_json_is_silent(self, tmp_path):
        # Arrange
        (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert warnings == []

    def test_name_with_app_suffix_accepted(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "my_app"
        write_manifest(tmp_path, data)
        errors = validate_manifest(tmp_path)
        # Act
        name_errors = [e for e in errors if "_app" in e or "-app" in e]
        # Assert
        assert name_errors == []

    def test_version_key_forbidden_adds_error(self, tmp_path):
        # A hand-written 'version' key is forbidden — the version derives at
        # runtime from the installed 'pip_package' (importlib.metadata).
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["name"] = "my_app"
        data["version"] = "1.0.0"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("must NOT declare 'version'" in e for e in errors)

    def test_missing_pip_package_adds_error(self, tmp_path):
        # pip_package is required — the single source of truth for the version.
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS if k != "pip_package"}
        data["name"] = "my_app"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("pip_package" in e for e in errors)

    # --- mount_policy jail contract (closed when present, open when absent) ---

    def test_login_only_mount_policy_is_valid(self, tmp_path):
        # Arrange — the pre-jail contract (creator manifest shape)
        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mount_policy"] = {"login_required": True}
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert errors == []

    def test_file_touching_without_jail_is_rejected(self, tmp_path):
        # Arrange
        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mount_policy"] = {"login_required": True, "touches_files": True}
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("jail" in e for e in errors)

    def test_typo_jail_scope_is_rejected(self, tmp_path):
        # Arrange
        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mount_policy"] = {
            "login_required": True,
            "touches_files": True,
            "jail": {"scope": "users"},
        }
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("scope" in e for e in errors)

    def test_full_figrecipe_mount_policy_is_valid(self, tmp_path):
        # Arrange — the reference declaration the leaf adopts
        from scitex_sdk.app.jail import FIGRECIPE_MOUNT_POLICY_REFERENCE

        data: dict = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["mount_policy"] = dict(FIGRECIPE_MOUNT_POLICY_REFERENCE)
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert errors == []


class TestSlugIsMountLeaf:
    """slug becomes /apps/<slug>/: malformed is an ERROR."""

    def test_malformed_slug_is_an_error(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["slug"] = "Bad_Slug!"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert any("'slug'" in e for e in errors)

    def test_wellformed_slug_passes(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["slug"] = "my-app"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert not [e for e in errors if "'slug'" in e]


class TestLabelFamilyFormIsAdvisory:
    """label 'SciTeX <Name>' is taste: warn, never fail."""

    def test_bare_label_is_not_an_error(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["slug"] = "my-app"
        data["label"] = "Storage"
        write_manifest(tmp_path, data)
        # Act
        errors = validate_manifest(tmp_path)
        # Assert
        assert not [e for e in errors if "'label'" in e]

    def test_bare_label_is_an_advisory(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["label"] = "Storage"
        write_manifest(tmp_path, data)
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert any("SciTeX <Name>" in w for w in warnings)

    def test_family_label_raises_no_advisory(self, tmp_path):
        # Arrange
        data = {k: "value" for k in MANIFEST_REQUIRED_KEYS}
        data["label"] = "SciTeX Stats"
        write_manifest(tmp_path, data)
        # Act
        warnings = validate_manifest_advisory(tmp_path)
        # Assert
        assert not [w for w in warnings if "SciTeX <Name>" in w]


# EOF
