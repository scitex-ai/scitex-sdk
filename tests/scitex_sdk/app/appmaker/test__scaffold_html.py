"""Generated consumer apps must satisfy the actual SDK ownership auditor."""

from __future__ import annotations

import pytest
from django.template import Context, Template
from scitex_dev._cli.audit._project._violation import Violation

from scitex_sdk._audit_plugin import check_header_contract
from scitex_sdk.app.appmaker import init_app


@pytest.mark.parametrize("frontend", ["html", "react"])
def test_generated_consumer_passes_actual_header_ownership_auditor(tmp_path, frontend):
    # Arrange
    init_app(
        tmp_path, "generated_probe_app", label="Generated Probe", frontend_type=frontend
    )
    # Act
    findings = []
    check_header_contract(tmp_path, Violation, findings)
    # Assert
    assert findings == []


def test_generated_partial_renders_sdk_mount_metadata_and_module(tmp_path):
    # Arrange
    init_app(tmp_path, "generated_probe_app", label="Generated Probe")
    source = (
        tmp_path
        / "generated_probe_app/templates/generated_probe_app/index_partial.html"
    ).read_text()
    # Act
    html = Template(source).render(
        Context(
            {"app_version": "1.2.3", "app_scope": "project", "current_project": None}
        )
    )
    # Assert
    assert (
        "data-stx-app-header" in html
        and 'data-app-title="Generated Probe"' in html
        and 'data-app-version="1.2.3"' in html
        and "scitex_sdk/ui/js/app/app-header.js" in html
        and "stx-app-header__title" not in html
    )
