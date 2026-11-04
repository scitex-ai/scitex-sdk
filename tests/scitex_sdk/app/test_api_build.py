"""Source-proven metadata production never executes the declaring package."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scitex_sdk.app.api_build import (
    ApiMetadataBuildError,
    build_inert_api_metadata,
    prepare_hatch_api_metadata,
    write_inert_api_metadata,
)
from scitex_sdk.app.api_mount import parse_inert_descriptor


@pytest.fixture
def declaration(tmp_path):
    root = tmp_path / "project"
    package = root / "src/demo_api"
    package.mkdir(parents=True)
    marker = tmp_path / "EXECUTED"
    (package / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('must not import consumer')\n"
    )
    (package / "views.py").write_text("def items(request):\n    return {'items': []}\n")
    source = """from scitex_sdk.app.api_plugin import ApiPlugin, ApiRoute, ApiSchema, ApiField, AuthScope, RateLimit
plugin = ApiPlugin(id="demo", title="Demo", api_version="1", routes=(
    ApiRoute(path="items", methods=("GET",), handler="demo_api.views:items",
        auth=AuthScope(public=True, project_scope="none"), rate=RateLimit(rate_class="free", compute_cost="low"),
        response=ApiSchema(name="Items", fields=(ApiField(name="items", type="array"),)), read_only=True),))
"""
    (package / "descriptor.py").write_text(source)
    (root / "pyproject.toml").write_text(
        '[project]\nname="demo-api"\nversion="1.0"\n[project.entry-points."scitex.apis"]\ndemo="demo_api.descriptor:plugin"\n'
    )
    return root, package, marker


def test_source_roundtrip_has_real_operations_without_importing_consumer(declaration):
    # Arrange
    root, _, marker = declaration
    # Act
    data = build_inert_api_metadata(root)
    plugin = parse_inert_descriptor(data.decode())
    # Assert
    assert (plugin.id, list(plugin.openapi_fragment()["paths"]), marker.exists()) == (
        "demo",
        ["/items"],
        False,
    )


def test_constructor_looking_consumer_expression_is_refused_without_execution(
    declaration,
):
    # Arrange
    root, package, marker = declaration
    source = (
        (package / "descriptor.py")
        .read_text()
        .replace(
            'title="Demo"', f'title=__import__("pathlib").Path({str(marker)!r}).touch()'
        )
    )
    (package / "descriptor.py").write_text(source)
    # Act / Assert
    with pytest.raises(ApiMetadataBuildError):
        build_inert_api_metadata(root)
    assert not marker.exists()


def test_missing_handler_refuses_output_instead_of_false_green_metadata(
    declaration, tmp_path
):
    # Arrange
    root, package, _ = declaration
    (package / "views.py").unlink()
    output = tmp_path / "scitex_api.json"
    # Act / Assert
    with pytest.raises(ApiMetadataBuildError):
        write_inert_api_metadata(root, output)
    assert not output.exists()


def test_escaping_source_symlink_is_not_imported_or_serialized(declaration, tmp_path):
    # Arrange
    root, package, marker = declaration
    external = tmp_path / "external.py"
    external.write_bytes((package / "descriptor.py").read_bytes())
    (package / "descriptor.py").unlink()
    (package / "descriptor.py").symlink_to(external)
    # Act / Assert
    with pytest.raises(ApiMetadataBuildError):
        build_inert_api_metadata(root)
    assert not marker.exists()


def test_multiple_valid_declarations_cannot_silently_choose_one(declaration):
    # Arrange
    root, package, _ = declaration
    source = (package / "descriptor.py").read_text()
    (package / "descriptor.py").write_text(
        source
        + source.split("plugin = ", 1)[1]
        .join(["\nother = ", ""])
        .replace('id="demo"', 'id="other"')
    )
    metadata = root / "pyproject.toml"
    metadata.write_text(metadata.read_text() + 'other="demo_api.descriptor:other"\n')
    # Act / Assert
    with pytest.raises(ApiMetadataBuildError, match="exactly one"):
        build_inert_api_metadata(root)


@pytest.mark.parametrize("symlink", [False, True])
def test_writer_never_clobbers_existing_or_symlinked_output(
    declaration, tmp_path, symlink
):
    # Arrange
    root, _, _ = declaration
    original = tmp_path / "sentinel"
    original.write_text("preserve")
    output = tmp_path / "scitex_api.json"
    if symlink:
        output.symlink_to(original)
    else:
        output.write_text("preserve")
    # Act / Assert
    with pytest.raises(FileExistsError):
        write_inert_api_metadata(root, output)
    assert (original.read_text(), output.read_text()) == ("preserve", "preserve")


def test_hatch_adapter_uses_actual_metadata_naming_and_owned_temporary_output(
    declaration,
):
    # Arrange
    root, _, marker = declaration
    hook = SimpleNamespace(
        root=root,
        target_name="wheel",
        metadata=SimpleNamespace(
            core=SimpleNamespace(name="demo-api", raw_name="Demo.API"), version="1.0"
        ),
        build_config=SimpleNamespace(strict_naming=False, get_force_include=lambda: {}),
    )
    build = {}
    # Act
    temporary = prepare_hatch_api_metadata(hook, build)
    try:
        path, target = next(iter(build["force_include"].items()))
        result = (target, json.loads(Path(path).read_text())["id"], marker.exists())
    finally:
        temporary.cleanup()
    # Assert
    assert result == ("Demo.API-1.0.dist-info/scitex_api.json", "demo", False)


@pytest.mark.parametrize(
    "destination",
    [
        "demo_api-1.0.dist-info/scitex_api.json",
        "demo_api-1.0.dist-info",
        ".",
        "/",
        "./demo_api-1.0.dist-info/",
    ],
)
@pytest.mark.parametrize("configured", [False, True])
def test_hatch_adapter_refuses_a_competing_metadata_producer(
    declaration, destination, configured
):
    # Arrange
    root, _, _ = declaration
    hook = SimpleNamespace(
        root=root,
        target_name="wheel",
        metadata=SimpleNamespace(
            core=SimpleNamespace(name="demo-api", raw_name="demo-api"), version="1.0"
        ),
        build_config=SimpleNamespace(
            strict_naming=True,
            get_force_include=lambda: {"other": destination} if configured else {},
        ),
    )
    # Act / Assert
    with pytest.raises(ApiMetadataBuildError, match="another producer"):
        prepare_hatch_api_metadata(
            hook, {"force_include": {} if configured else {"other": destination}}
        )


def test_normal_sdist_rebuild_has_exactly_one_descriptor_and_record_row(
    declaration, tmp_path
):
    # Arrange: a real backend rebuild, with a consumer that raises on import.
    import csv
    import io
    import tarfile
    import zipfile

    from hatchling.builders.sdist import SdistBuilder
    from hatchling.builders.wheel import WheelBuilder

    root, _, marker = declaration
    metadata = root / "pyproject.toml"
    metadata.write_text(
        metadata.read_text()
        + """
[build-system]
requires = ["hatchling>=1.27", "scitex-sdk>=0.3.20"]
build-backend = "hatchling.build"
[tool.hatch.build.hooks.custom]
path = "hatch_build.py"
[tool.hatch.build.targets.wheel]
packages = ["src/demo_api"]
"""
    )
    (
        root / "hatch_build.py"
    ).write_text("""from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from scitex_sdk.app.api_build import prepare_hatch_api_metadata
class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        self.temporary = prepare_hatch_api_metadata(self, build_data)
    def finalize(self, version, build_data, artifact_path):
        if self.temporary is not None:
            self.temporary.cleanup()
""")
    expected = build_inert_api_metadata(root)
    # Act
    sdist = Path(next(SdistBuilder(str(root)).build(directory=str(tmp_path / "dist"))))
    extracted = tmp_path / "unpacked"
    with tarfile.open(sdist) as archive:
        for member in archive.getmembers():
            if member.isfile():
                destination = extracted / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(member).read())
    rebuilt = next(extracted.iterdir())
    wheel = next(WheelBuilder(str(rebuilt)).build(directory=str(tmp_path / "wheels")))
    with zipfile.ZipFile(wheel) as archive:
        descriptors = [n for n in archive.namelist() if n.endswith("/scitex_api.json")]
        record = next(n for n in archive.namelist() if n.endswith(".dist-info/RECORD"))
        rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
        observation = (
            len(descriptors),
            sum(row[0].endswith("/scitex_api.json") for row in rows),
            archive.read(descriptors[0]),
            marker.exists(),
        )
    # Assert
    assert observation == (1, 1, expected, False)
