"""Real SDK declarations are validated without running any consumer code."""

import pytest

from scitex_sdk._api_hook import check_payload
from scitex_sdk.app._api_contract import scan_web_contract
from scitex_sdk.app.api_mount import dump_inert_descriptor, parse_inert_descriptor

_DECLARATION = """from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, AuthScope, RateLimit
from pathlib import Path
Path(__file__).with_name('EXECUTED').write_text('unsafe')
PATH = 'ping'
def ping(request):
    raise RuntimeError('business code must never run')
PLUGIN = ApiPlugin(id='demo', title='Demo', api_version='1.0.0', routes=[
    ApiRoute(path=PATH, methods=['GET'], rate=RateLimit(rate_class='free', compute_cost='low'),
             auth=AuthScope(public=True, project_scope='none'), handler='demo.api:ping')
])
"""


@pytest.fixture
def api_repo(tmp_path):
    root = tmp_path
    package = root / "src/demo"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (root / "pyproject.toml").write_text(
        '[project]\nname="demo"\n[project.entry-points."scitex.apis"]\ndemo="demo.api:PLUGIN"\n'
    )
    (package / "api.py").write_text(_DECLARATION)
    return root


def test_real_descriptor_passes_without_consumer_execution(api_repo):
    # Arrange
    marker = api_repo / "src/demo/EXECUTED"
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert (findings, marker.exists()) == ([], False)


@pytest.mark.parametrize(
    "metadata",
    [
        "project = []\n",
        "[project]\nentry-points = []\n",
        '[project.entry-points]\n"scitex.apis" = []\n',
    ],
)
def test_malformed_metadata_tables_report_a_finding(api_repo, metadata):
    # Malformed TOML structure must produce an audit finding, never a crash.
    (api_repo / "pyproject.toml").write_text(metadata)
    findings = scan_web_contract(api_repo)
    assert len(findings) == 1
    assert findings[0].path == "pyproject.toml"
    assert "metadata cannot be verified" in findings[0].detail
    assert not (api_repo / "src/demo/EXECUTED").exists()


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("PATH = 'ping'", "PATH = '/escape'"),
        ("methods=['GET']", "methods=['GET', 'GET']"),
        ("handler='demo.api:ping'", "handler='demo.api:missing'"),
        ("handler='demo.api:ping'", "handler='foreign.api:ping'"),
        ("id='demo'", "id='other'"),
        ("PATH = 'ping'", "PATH = str('ping')"),
        ("PATH = 'ping'", "PATH = PATH"),
        (
            "PATH = 'ping'",
            "PATH = Path(__file__).with_name('EXECUTED').write_text('unsafe')",
        ),
        ("PLUGIN = ApiPlugin", "PLUGIN = fake_constructor"),
    ],
)
def test_invalid_or_unproven_sources_refuse_without_execution(api_repo, old, new):
    # Arrange
    path = api_repo / "src/demo/api.py"
    path.write_text(path.read_text().replace(old, new))
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert (len(findings), (path.parent / "EXECUTED").exists()) == (1, False)


def test_owned_relative_reexport_and_class_handler(api_repo):
    # Arrange
    package = api_repo / "src/demo"
    (package / "api.py").write_text(
        _DECLARATION.replace(
            "handler='demo.api:ping'", "handler='demo.handlers:Views.ping'"
        )
    )
    (package / "handlers.py").write_text(
        "class Views:\n    def ping(self, request):\n        raise RuntimeError()\n"
    )
    (package / "export.py").write_text("from .api import PLUGIN\n")
    metadata = api_repo / "pyproject.toml"
    metadata.write_text(
        metadata.read_text().replace("demo.api:PLUGIN", "demo.export:PLUGIN")
    )
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert findings == []


def test_cyclic_reexport_is_explicit_failure(api_repo):
    # Arrange
    path = api_repo / "src/demo/api.py"
    path.write_text("from .cycle import PLUGIN\n")
    (path.parent / "cycle.py").write_text("from .api import PLUGIN\n")
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert "cyclic" in findings[0].detail


def test_native_pre_edit_evaluates_overlay_and_never_changes_disk(api_repo):
    # Arrange
    path = api_repo / "src/demo/api.py"
    before = path.read_bytes()
    payload = {
        "cwd": str(api_repo),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(path),
            "old_string": "PATH = 'ping'",
            "new_string": "PATH = '/escape'",
        },
    }
    # Act
    findings = check_payload(payload)
    # Assert
    assert (len(findings), path.read_bytes() == before) == (1, True)


def test_pure_inert_parser_reuses_actual_sdk_validation(api_repo):
    # Arrange
    from scitex_sdk.app._api_source import SourceReader

    plugin = SourceReader(api_repo).binding("demo.api", "PLUGIN")
    # Act
    restored = parse_inert_descriptor(dump_inert_descriptor(plugin))
    # Assert
    assert restored.openapi_fragment() == plugin.openapi_fragment()


def test_dev_project_dispatcher_reports_sdk_api_rule(api_repo):
    # Arrange
    from scitex_dev._cli.audit._project._plugins import load_plugins
    from scitex_dev._cli.audit._project._violation import Violation

    path = api_repo / "src/demo/api.py"
    path.write_text(path.read_text().replace("PATH = 'ping'", "PATH = '/escape'"))
    findings = []
    # Act
    for check in load_plugins().checks:
        if check.__module__ == "scitex_sdk._audit_plugin":
            check(api_repo, Violation, findings)
    # Assert
    assert [(f.rule, f.severity) for f in findings] == [("PS-SDK-WEB", "E")]


@pytest.mark.parametrize(
    "suffix",
    [
        "if True:\n    PLUGIN = None\n",
        "PLUGIN, other = (None, None)\n",
        "del PLUGIN\n",
        "(PLUGIN := None)\n",
        "match 1:\n    case PLUGIN:\n        pass\n",
    ],
)
def test_conditional_rebinding_cannot_hide_behind_valid_descriptor(api_repo, suffix):
    # Arrange
    path = api_repo / "src/demo/api.py"
    path.write_text(path.read_text() + "\n" + suffix)
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert "overwritten" in findings[0].detail


def test_native_dev_dispatcher_executes_web_rule(api_repo):
    # Arrange
    from scitex_dev.hooks._dispatch import dispatch

    path = api_repo / "src/demo/api.py"
    payload = {
        "cwd": str(api_repo),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": str(path),
            "old_string": "PATH = 'ping'",
            "new_string": "PATH = '/escape'",
        },
    }
    # Act
    findings = dispatch(payload, provider="scitex-sdk")
    # Assert
    assert any("PS-SDK-WEB" in str(finding) for finding in findings)


def test_duplicate_schema_error_comes_from_existing_sdk(api_repo):
    # Arrange
    path = api_repo / "src/demo/api.py"
    source = _DECLARATION.replace(
        "ApiPlugin, ApiRoute, AuthScope, RateLimit",
        "ApiPlugin, ApiRoute, AuthScope, RateLimit, ApiSchema, ApiField",
    )
    source = source.replace(
        "handler='demo.api:ping'",
        "handler='demo.api:ping', request=ApiSchema(name='Same', fields=[ApiField(name='x', type='string')]), response=ApiSchema(name='Same', fields=[ApiField(name='y', type='string')])",
    )
    path.write_text(source)
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert "schema name" in findings[0].detail


def test_native_post_shell_reports_actual_changed_declaration(api_repo):
    # Arrange
    import subprocess

    from scitex_dev.hooks._dispatch import dispatch

    subprocess.run(["git", "init", "-q", str(api_repo)], check=True)
    path = api_repo / "src/demo/api.py"
    path.write_text(path.read_text().replace("PATH = 'ping'", "PATH = '/escape'"))
    payload = {
        "hook_event_name": "PostToolUse",
        "cwd": str(api_repo),
        "tool_name": "Bash",
        "tool_input": {"command": "already executed"},
    }
    # Act
    findings = dispatch(payload, provider="scitex-sdk")
    # Assert
    assert any("PS-SDK-WEB" in str(finding) for finding in findings)


@pytest.mark.parametrize(
    "stage_command", [("diff", "--name-only"), ("add", "-u")],
    ids=["unstaged", "staged"],
)
def test_post_shell_reports_deleted_owned_handler(api_repo, stage_command):
    # A deletion alone must invalidate the still-declared handler binding.
    # Arrange
    import subprocess

    from scitex_dev.hooks._dispatch import dispatch

    from scitex_sdk._header_hook import _source_changes

    path = api_repo / "src/demo/api.py"
    path.write_text(
        path.read_text().replace("demo.api:ping", "demo.handlers:ping")
    )
    handler = path.with_name("handlers.py")
    handler.write_text("def ping(request):\n    raise RuntimeError('never run')\n")
    subprocess.run(["git", "init", "-q", str(api_repo)], check=True)
    subprocess.run(["git", "-C", str(api_repo), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(api_repo), "-c", "user.name=SDK fixture",
            "-c", "user.email=sdk-fixture@example.invalid", "commit", "-qm", "fixture",
        ],
        check=True,
    )
    handler.unlink()
    subprocess.run(
        ["git", "-C", str(api_repo), *stage_command], check=True, capture_output=True
    )
    payload = {
        "hook_event_name": "PostToolUse",
        "cwd": str(api_repo),
        "tool_name": "Bash",
        "tool_input": {"command": "already executed"},
    }

    # Act
    findings = dispatch(payload, provider="scitex-sdk")

    # Assert
    # Chrome's existing changed-file policy remains unaffected.
    observed = (
        any("PS-SDK-WEB" in str(f) and "demo.handlers" in str(f) for f in findings),
        (path.parent / "EXECUTED").exists(),
        _source_changes(payload)[2],
    )
    assert observed == (True, False, set())


def test_missing_api_scanner_refuses_provider_loading(tmp_path):
    # Arrange
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    import scitex_sdk

    package = Path(scitex_sdk.__file__).parent
    for source in package.rglob("*.py"):
        relative = source.relative_to(package)
        if relative == Path("app/_api_contract.py"):
            continue
        target = tmp_path / "scitex_sdk" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    program = (
        "import sys;sys.path.insert(0,sys.argv[1]);"
        "from scitex_sdk._audit_plugin import get_plugin;get_plugin()"
    )
    # Act
    result = subprocess.run(
        [sys.executable, "-I", "-c", program, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    # Assert
    assert (
        result.returncode != 0
        and "No module named 'scitex_sdk.app._api_contract'" in result.stderr
    )


@pytest.mark.parametrize(
    ("fallback", "expected"),
    [
        ("raise ImportError('install the SDK extra')", 0),
        ("ApiPlugin = object", 1),
    ],
)
def test_optional_sdk_import_guard_has_no_fallback_factory(
    api_repo, fallback, expected
):
    # Arrange
    path = api_repo / "src/demo/api.py"
    line, rest = _DECLARATION.split("\n", 1)
    path.write_text(
        "try:\n    " + line + "\nexcept ImportError:\n    " + fallback + "\n" + rest
    )
    # Act
    findings = scan_web_contract(api_repo)
    # Assert
    assert len(findings) == expected
