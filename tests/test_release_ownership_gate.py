"""Release phase controls: ownership, persisted contracts and complete inventory."""
import copy
import importlib.metadata
import json
from pathlib import Path

import pytest

from scripts import ownership_gate as gate
from scripts import retirement_graphs as graphs


@pytest.mark.parametrize("code", [
    "import scitex_app", "from scitex_ui.widgets import Button",
    "importlib.import_module('scitex_app.urls')", "__import__('scitex_ui')",
    "include('scitex_app.urls')", "INSTALLED_APPS=['scitex_app.apps.Config']",
    "settings.configure(INSTALLED_APPS=['scitex_ui'])",
    "TEMPLATES=[{'OPTIONS': {'context_processors':['scitex_app.context_processors.app']}}]",
    "sys.modules['scitex_ui']=replacement",
    "class Config(AppConfig):\n    name='scitex_app'",
])
def test_executable_retired_python_reference_is_detected(code):
    # Arrange
    source = code
    # Act
    references = gate.python_imports(source)
    # Assert
    assert references


@pytest.mark.parametrize("code", [
    "from scitex_sdk import ui as scitex_ui",
    "from scitex_sdk.app.apps import SciTeXAppConfig",
    "class Config(AppConfig):\n    name='scitex_sdk.app'\n    label='scitex_app'",
    "models.ForeignKey('scitex_app.ChatSession', on_delete=models.CASCADE)",
    "os.getenv('SCITEX_APP_PORT'); tag='scitex_ui'; block='scitex_app_content'",
    "context={'scitex_app': value}; config_dir='.scitex/ui'",
    "# import scitex_app\nexample='from scitex_ui import Widget'",
])
def test_persisted_labels_and_canonical_local_aliases_are_preserved(code):
    # Arrange
    source = code
    # Act
    references = gate.python_imports(source)
    # Assert
    assert references == []


@pytest.mark.parametrize("code", [
    "import '@scitex/app';", "import {x} from '@scitex/ui/react';",
    "export {x} from '@scitex/ui';", "import('@scitex/app/bridge');",
    "const x=require('@scitex/ui');",
    "import 'scitex-ui/css/app.css';", "import {x} from 'scitex-app/bridge';",
])
def test_executable_retired_frontend_reference_is_detected(code):
    # Arrange
    source = code
    # Act
    references = gate.frontend_imports(source)
    # Assert
    assert references


@pytest.mark.parametrize("code", [
    "import {x} from '@scitex/sdk/ui/react';",
    "// import '@scitex/app'\n/* export {x} from '@scitex/ui' */",
    'const example="import \'@scitex/app\'";',
    "const example=`from '@scitex/ui'`;",
])
def test_frontend_comments_prose_and_canonical_imports_are_preserved(code):
    # Arrange
    source = code
    # Act
    references = gate.frontend_imports(source)
    # Assert
    assert references == []


def test_npm_dependency_cannot_hide_in_optional_group(tmp_path):
    # Arrange
    path = tmp_path / "package.json"
    path.write_text(json.dumps({"optionalDependencies": {"@scitex/ui": "*"}}))
    # Act
    references = gate.file_imports(path)
    # Assert
    assert references[0]["reference"] == "@scitex/ui"


def empty_observation():
    return {"direct_sdk_ownership_errors": [], "retired_distributions": [],
            "retired_module_specs": [], "retired_import_references": [],
            "unreadable_execution_files": [], "installed_versions": {"scitex-sdk": "0.3.0"}}


@pytest.mark.parametrize("mode,field,value,expected", [
    ("retirement", "retired_distributions", ["scitex-app"], 1),
    ("retirement", "retired_module_specs", [{"module": "scitex_ui"}], 1),
    ("retirement", "retired_import_references", [{"reference": "scitex_app"}], 1),
    ("retirement", "unreadable_execution_files", [{"member": "broken.py"}], 1),
    ("retirement", "direct_sdk_ownership_errors", ["direct retired requirement"], 1),
    ("retirement", "retired_distributions", [], 0),
    ("bootstrap-observation", "retired_distributions", ["scitex-app"], 0),
    ("bootstrap-observation", "direct_sdk_ownership_errors", ["direct retired requirement"], 1),
])
def test_phase_failure_status_cannot_mask_direct_or_retirement_defects(mode, field, value, expected):
    # Arrange
    observation = empty_observation()
    observation[field] = value
    # Act
    result = gate.evaluate(observation, mode, "owned-control")
    # Assert
    assert result[1] == expected


def test_bootstrap_legacy_graph_is_explicitly_incomplete():
    # Arrange
    observation = empty_observation()
    observation["retired_distributions"] = ["scitex-app"]
    # Act
    report = gate.evaluate(observation, "bootstrap-observation", "owned-control")[0]
    # Assert
    assert report["status"] == "DEPENDENCY_RETIREMENT_NOT_READY"


def test_one_clean_graph_never_claims_complete_dependency_retirement():
    # Arrange
    observation = empty_observation()
    # Act
    report = gate.evaluate(observation, "retirement", "owned-control")[0]
    # Assert
    assert report["dependency_retirement_ready"] is False


class FixtureDistribution:
    """Minimal real-shaped installed metadata, never a published version override."""
    metadata = {"Name": "scitex-sdk"}
    version = "0.3.0"
    entry_points = []
    files = []
    requires = []

    def locate_file(self, member):
        return member


def fixture_observe(monkeypatch, distribution):
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: [distribution])
    monkeypatch.setattr(gate.importlib.util, "find_spec", lambda name: None)
    return gate.observe()


def test_direct_optional_retired_requirement_blocks_bootstrap(monkeypatch):
    # Arrange
    distribution = FixtureDistribution()
    distribution.requires = ['SciTeX_UI>=0.23; extra == "unused"']
    # Act
    observation = fixture_observe(monkeypatch, distribution)
    # Assert
    assert gate.evaluate(observation, "bootstrap-observation", "owned-control")[1] == 1


def test_missing_sdk_file_inventory_blocks_bootstrap(monkeypatch):
    # Arrange
    distribution = FixtureDistribution()
    distribution.files = None
    # Act
    observation = fixture_observe(monkeypatch, distribution)
    # Assert
    assert observation["direct_sdk_ownership_errors"]


def test_canonical_component_entrypoint_names_do_not_require_retired_modules(monkeypatch):
    # Arrange
    distribution = FixtureDistribution()
    distribution.entry_points = [importlib.metadata.EntryPoint(
        name="scitex-app", value="scitex_sdk.app", group="scitex_dev.docs")]
    # Act
    observation = fixture_observe(monkeypatch, distribution)
    # Assert
    assert observation["retired_import_references"] == []


def test_retired_entrypoint_target_blocks_bootstrap(monkeypatch):
    # Arrange
    distribution = FixtureDistribution()
    distribution.entry_points = [importlib.metadata.EntryPoint(
        name="arbitrary", value="scitex_app:main", group="console_scripts")]
    # Act
    observation = fixture_observe(monkeypatch, distribution)
    # Assert
    assert observation["direct_sdk_ownership_errors"]


@pytest.mark.parametrize("requirement,extras,expected", [
    ("scitex-sdk>=0.3.0", [], True),
    ("scitex-sdk>=0.2.0", [], False),
    ('scitex-sdk>=0.3.0; extra == "gui"', [], False),
    ('scitex-sdk>=0.3.0; extra == "gui"', ["gui"], True),
    ("scitex-ui>=0.23.0", [], False),
])
def test_active_consumer_sdk_floor_is_checked_in_requested_runtime_group(requirement, extras, expected):
    # Arrange
    metadata = {"requires_dist": [requirement]}
    # Act
    canonical = graphs.requires_canonical_sdk(metadata, extras)
    # Assert
    assert canonical is expected


@pytest.mark.parametrize("omitted", sorted(graphs.REQUIRED_GRAPHS))
def test_audited_consumer_cannot_be_omitted(omitted):
    # Arrange
    policy = json.loads(Path("scripts/app-ui-retirement-graphs.json").read_text())
    policy["graphs"] = [row for row in policy["graphs"] if row["name"] != omitted]
    # Act
    # Assert
    with pytest.raises(ValueError, match="every audited consumer"):
        graphs.validate_policy(policy)


def test_unknown_canonical_release_floor_refuses_policy():
    # Arrange
    policy = json.loads(Path("scripts/app-ui-retirement-graphs.json").read_text())
    # Act
    # Assert
    with pytest.raises(ValueError, match="genuine canonical release floors"):
        graphs.validate_policy(copy.deepcopy(policy))


@pytest.mark.parametrize("policy", [None, [], {}, {"schema": True},
    {"schema": 1, "graphs": None}, {"schema": 1, "graphs": [None]},
    {"schema": 1, "graphs": [{"name": []}]},
])
def test_malformed_policy_shape_fails_cleanly(policy):
    # Arrange
    malformed = policy
    # Act
    # Assert
    with pytest.raises(ValueError):
        graphs.validate_policy(malformed)


@pytest.mark.parametrize("field,value", [
    ("extras", "gui"), ("extras", ["gui,all"]), ("distribution", "scitex-sdk[all]"),
    ("minimum_canonical_version", []), ("canonical_source_commit", 42),
    ("sdk_requirement", "none"),
])
def test_malformed_graph_cannot_mask_registration_failure(field, value):
    # Arrange
    policy = json.loads(Path("scripts/app-ui-retirement-graphs.json").read_text())
    policy["graphs"][0][field] = value
    # Act
    # Assert
    with pytest.raises(ValueError):
        graphs.validate_policy(policy)


def test_bare_npm_retired_dependency_is_detected(tmp_path):
    # Arrange
    path = tmp_path / "package.json"
    path.write_text(json.dumps({"dependencies": {"scitex-ui": "*"}}))
    # Act
    references = gate.file_imports(path)
    # Assert
    assert references[0]["reference"] == "scitex-ui"


def invoke_incomplete_policy(monkeypatch, tmp_path):
    policy = Path("scripts/app-ui-retirement-graphs.json").resolve()
    monkeypatch.setattr("sys.argv", ["retirement_graphs", "--policy", str(policy),
        "--scratch", str(tmp_path / "must-not-exist"), "--output", str(tmp_path / "report.json")])
    return graphs.main()


def test_unregistered_policy_main_returns_failure(monkeypatch, tmp_path):
    # Arrange
    scratch = tmp_path
    # Act
    code = invoke_incomplete_policy(monkeypatch, scratch)
    # Assert
    assert code == 1


def test_unregistered_policy_cannot_create_resolver_environment(monkeypatch, tmp_path):
    # Arrange
    scratch = tmp_path
    # Act
    invoke_incomplete_policy(monkeypatch, scratch)
    # Assert
    assert not (scratch / "must-not-exist").exists()


def test_foreign_distribution_retired_import_is_not_omitted(monkeypatch, tmp_path):
    # Arrange
    module = tmp_path / "foreignpkg.py"
    module.write_text("from scitex_ui import widgets\n")
    foreign = FixtureDistribution()
    foreign.metadata = {"Name": "foreign-consumer"}
    foreign.files = [Path("foreignpkg.py")]
    foreign.locate_file = lambda member: tmp_path / member
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: [FixtureDistribution(), foreign])
    monkeypatch.setattr(gate.importlib.util, "find_spec", lambda name: None)
    # Act
    observation = gate.observe()
    # Assert
    assert observation["retired_import_references"][0]["distribution"] == "foreign-consumer"


def test_duplicate_sdk_metadata_cannot_mask_direct_ownership(monkeypatch):
    # Arrange
    monkeypatch.setattr(importlib.metadata, "distributions", lambda: [FixtureDistribution(), FixtureDistribution()])
    monkeypatch.setattr(gate.importlib.util, "find_spec", lambda name: None)
    # Act
    observation = gate.observe()
    # Assert
    assert observation["direct_sdk_ownership_errors"]


def test_malformed_npm_dependency_inventory_is_not_silently_ignored(tmp_path):
    # Arrange
    path = tmp_path / "package.json"
    path.write_text(json.dumps({"dependencies": "scitex-ui"}))
    # Act
    # Assert
    with pytest.raises(ValueError, match="dependency objects"):
        gate.file_imports(path)


def config_observation(monkeypatch, tmp_path):
    module = tmp_path / "scitex_config.py"
    module.write_text("SCITEX_APP_DIR = '.scitex/app'\nSCITEX_UI_DIR = '.scitex/ui'\n")
    distribution = FixtureDistribution()
    distribution.metadata = {"Name": "scitex-config"}
    distribution.version = "0.3.6"
    distribution.files = [Path("scitex_config.py")]
    distribution.locate_file = lambda member: tmp_path / member
    return fixture_observe(monkeypatch, distribution)


def test_config_graph_without_sdk_preserves_its_legitimate_contract(monkeypatch, tmp_path):
    # Arrange
    observation = config_observation(monkeypatch, tmp_path)
    # Act
    report, code = gate.evaluate(observation, "retirement", "config-core", sdk_requirement="none")
    # Assert
    assert code == 0 and report["status"] == "RETIREMENT_GRAPH_PASSED"
    assert report["sdk_required"] is False and report["dependency_retirement_ready"] is False


@pytest.mark.parametrize("mode,graph,requirement", [
    ("bootstrap-observation", "sdk-all", "owner"),
    ("bootstrap-observation", "config-core", "owner"),
    ("retirement", "sdk-all", "owner"),
    ("retirement", "writer-gui", "active"),
])
def test_missing_sdk_still_blocks_every_required_graph(monkeypatch, tmp_path, mode, graph, requirement):
    # Arrange
    observation = config_observation(monkeypatch, tmp_path)
    # Act
    report, code = gate.evaluate(observation, mode, graph, sdk_requirement=requirement)
    # Assert
    assert code == 1 and report["sdk_required"] is True
    assert "scitex-sdk is not installed" in report["direct_sdk_ownership_errors"]


@pytest.mark.parametrize("defect", ["retired-requirement", "retired-entrypoint", "missing-inventory"])
def test_optional_sdk_if_present_is_still_inspected(monkeypatch, defect):
    # Arrange
    distribution = FixtureDistribution()
    if defect == "retired-requirement":
        distribution.requires = ['scitex-ui>=0.23; extra == "unused"']
    elif defect == "retired-entrypoint":
        distribution.entry_points = [importlib.metadata.EntryPoint(
            name="arbitrary", value="scitex_app:main", group="console_scripts")]
    else:
        distribution.files = None
    observation = fixture_observe(monkeypatch, distribution)
    # Act
    report, code = gate.evaluate(observation, "retirement", "config-core", sdk_requirement="none")
    # Assert
    assert code == 1 and report["direct_sdk_ownership_errors"]


@pytest.mark.parametrize("graph", ["sdk-all", "writer-gui", "config-core"])
def test_graph_executor_carries_validated_sdk_classification(monkeypatch, tmp_path, graph):
    # Arrange
    row = next(row for row in json.loads(Path("scripts/app-ui-retirement-graphs.json").read_text())["graphs"]
               if row["name"] == graph)
    row["minimum_canonical_version"] = "0.3.6"
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        from subprocess import CompletedProcess
        return CompletedProcess(command, 0, json.dumps({"version": "0.3.6",
            "requires_dist": ["scitex-sdk>=0.3.0"], "provides_extra": row["extras"]}), "")
    monkeypatch.setattr(graphs.subprocess, "run", run)
    # Act
    result = graphs.run_graph(row, tmp_path)
    # Assert
    assert result["status"] == "PASSED"
    ownership = next(command for command in commands if "--mode" in command)
    assert ownership[ownership.index("--sdk-requirement") + 1] == row["sdk_requirement"]


@pytest.mark.parametrize("mode,graph", [
    ("bootstrap-observation", "config-core"), ("retirement", "sdk-all"),
    ("retirement", "figrecipe-gui"), ("retirement", "unknown-graph"),
])
def test_cli_cannot_relax_sdk_owner_requirement(monkeypatch, mode, graph):
    # Arrange
    monkeypatch.setattr("sys.argv", ["ownership_gate", "--mode", mode, "--graph", graph,
                                   "--sdk-requirement", "none"])
    # Act
    # Assert
    with pytest.raises(SystemExit) as exc:
        gate.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("mode,graph", [
    ("retirement", "figrecipe-gui"), ("retirement", "writer-gui"),
    ("retirement", "unknown-graph"), ("retirement", "sdk-all"),
    ("bootstrap-observation", "config-core"),
])
def test_evaluator_rejects_forged_optional_sdk_classification(mode, graph):
    # Arrange
    observation = empty_observation()
    observation["installed_versions"] = {"scitex-config": "0.3.6"}
    # Act
    # Assert
    with pytest.raises(ValueError):
        gate.evaluate(observation, mode, graph, sdk_requirement="none")
