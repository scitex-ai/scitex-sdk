"""Produce the existing installed API descriptor from owned inert source.

Only SDK constructors execute. Consumer modules, handlers and entry points
are never imported. This produces declaration data, never host admission.
"""

from __future__ import annotations

import os
import posixpath
import tempfile
from pathlib import Path

from ._api_contract import scan_web_contract
from ._api_source import SourceReader
from .api_mount import INERT_DESCRIPTOR_FILENAME, dump_inert_descriptor
from .api_plugin import ApiPlugin

__all__ = [
    "ApiMetadataBuildError",
    "build_inert_api_metadata",
    "write_inert_api_metadata",
    "prepare_hatch_api_metadata",
]


class ApiMetadataBuildError(ValueError):
    """A declared API cannot be represented by proven installed metadata."""


def build_inert_api_metadata(project_root) -> bytes:
    """Serialize one source-proven provider into the current inert format.

    The current distribution-level reader supports one descriptor. Multiple
    declarations are refused rather than arbitrarily selecting or dropping one.
    Unsupported/dynamic source remains a build failure, not an import fallback.
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    root = Path(project_root).resolve()
    findings = scan_web_contract(root)
    if findings:
        raise ApiMetadataBuildError("; ".join(row.detail for row in findings))
    try:
        text = (root / "pyproject.toml").read_text(encoding="utf-8")
        if len(text.encode()) > 1_000_000:
            raise ValueError("project metadata byte limit exceeded")
        project = tomllib.loads(text).get("project", {})
        declarations = project.get("entry-points", {}).get("scitex.apis", {})
        if not isinstance(declarations, dict) or len(declarations) != 1:
            raise ValueError(
                "the installed inert format requires exactly one scitex.apis declaration"
            )
        name, target = next(iter(declarations.items()))
        if not isinstance(target, str) or target.count(":") != 1:
            raise ValueError("API entry point must name module:descriptor")
        module, attribute = target.split(":")
        if not attribute.isidentifier():
            raise ValueError("API descriptor binding must be an identifier")
        reader = SourceReader(root)
        plugin = reader.binding(module, attribute)
        if not isinstance(plugin, ApiPlugin) or plugin.id != name:
            raise ValueError("API descriptor and entry-point identity disagree")
        plugin.openapi_fragment()
        for route in plugin.routes:
            reader.handler(route.handler)
        data = (dump_inert_descriptor(plugin) + "\n").encode("utf-8")
        if len(data) > 1_000_000:
            raise ValueError("inert descriptor byte limit exceeded")
        return data
    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        SyntaxError,
        RecursionError,
    ) as exc:
        raise ApiMetadataBuildError(str(exc)) from exc


def write_inert_api_metadata(project_root, destination) -> Path:
    """Write a new output file; never overwrite a stale or symlinked resource."""
    data = build_inert_api_metadata(project_root)
    path = Path(destination)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o644), "wb") as stream:
        stream.write(data)
    return path


def prepare_hatch_api_metadata(hook, build_data):
    """Adapt the producer to a standard Hatch custom wheel build hook.

    Retain the returned TemporaryDirectory on the hook and clean it in
    finalize. Other backends can use the bytes/path functions directly.
    """
    try:
        from hatchling.builders.plugin.interface import BuilderInterface
    except ImportError as exc:
        raise ImportError("The Hatch API metadata adapter requires hatchling") from exc

    if hook.target_name != "wheel":
        return None
    core = hook.metadata.core
    name = core.name if hook.build_config.strict_naming else core.raw_name
    component = BuilderInterface.normalize_file_name_component(name)
    metadata_dir = f"{component}-{hook.metadata.version}.dist-info"
    target = f"{metadata_dir}/{INERT_DESCRIPTOR_FILENAME}"
    configured = hook.build_config.get_force_include()
    included = build_data.setdefault("force_include", {})
    destinations = (*configured.values(), *included.values())

    # Directory mappings can emit the same file, including a mapping to the
    # archive root. Refuse overlapping producers before Hatch traverses them.
    def overlaps(destination):
        normalized = posixpath.normpath(str(destination).replace("\\", "/")).lstrip("/")
        return normalized in ("", ".", metadata_dir, target)

    if any(overlaps(destination) for destination in destinations):
        raise ApiMetadataBuildError(
            "inert metadata target already has another producer"
        )
    temporary = tempfile.TemporaryDirectory(prefix="scitex-api-metadata-")
    try:
        output = write_inert_api_metadata(
            hook.root, Path(temporary.name) / INERT_DESCRIPTOR_FILENAME
        )
        included[str(output)] = target
        return temporary
    except BaseException:
        temporary.cleanup()
        raise
