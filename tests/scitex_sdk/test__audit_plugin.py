"""Real installed Dev project dispatcher discovers the SDK owner plugin."""

from scitex_dev._cli.audit._project._plugins import load_plugins
from scitex_dev._cli.audit._project._violation import Violation


def test_installed_dispatcher_executes_sdk_error_rule(tmp_path):
    # Arrange
    (tmp_path / "leaf.css").write_text(".stx-app-header__version {font-size:10px}")
    # Act
    bundle = load_plugins()
    findings = []
    for check in bundle.checks:
        if check.__module__ == "scitex_sdk._audit_plugin":
            check(tmp_path, Violation, findings)
    # Assert
    assert [(f.rule, f.severity) for f in findings] == [("PS-SDK-HEADER", "E")]
