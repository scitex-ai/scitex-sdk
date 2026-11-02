"""SDK-owned Web API quality checks over source declarations, without activation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._api_source import SourceReader, UnprovenApi
from .api_plugin import ApiPlugin, ApiPluginContractError


@dataclass(frozen=True)
class ApiFinding:
    """A source-backed contract failure or explicitly unproven binding."""

    path: str
    line: int
    detail: str


def scan_web_contract(repo_root, *, overlays=None):
    """Validate declared scitex.apis objects; absent presence belongs to Dev.

    Only SDK constructors execute. Consumer modules and handlers never import
    or run. Dynamic declarations remain explicit failures, not guessed validity.
    Passing proves source structure, not host admission or live availability.
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    root = Path(repo_root).resolve()
    overlays = {Path(p).resolve(): text for p, text in (overlays or {}).items()}
    project = root / "pyproject.toml"
    if not project.is_file() and project not in overlays:
        return []
    try:
        text = (
            overlays[project]
            if project in overlays
            else project.read_text(encoding="utf-8")
        )
        if len(text.encode()) > 1_000_000:
            raise ValueError("project metadata byte limit exceeded")
        data = tomllib.loads(text)
        declarations = (
            data.get("project", {}).get("entry-points", {}).get("scitex.apis", {})
        )
        if not isinstance(declarations, dict) or len(declarations) > 128:
            raise ValueError("scitex.apis must be a table with at most 128 entries")
    except (ValueError, OSError, TypeError) as exc:
        return [
            ApiFinding(
                "pyproject.toml",
                1,
                f"API metadata cannot be verified ({type(exc).__name__})",
            )
        ]
    findings = []
    for name, target in declarations.items():
        reader = SourceReader(root, overlays)
        location = "pyproject.toml"
        try:
            if not isinstance(target, str) or target.count(":") != 1:
                raise UnprovenApi("API entry point must name module:descriptor")
            module, attribute = target.split(":")
            if not attribute.isidentifier():
                raise UnprovenApi(
                    "API entry point must name an owned descriptor binding"
                )
            path, _ = reader.module(module)
            location = str(path.relative_to(root))
            plugin = reader.binding(module, attribute)
            if not isinstance(plugin, ApiPlugin):
                raise UnprovenApi("entry point is not an SDK ApiPlugin data object")
            if plugin.id != name:
                raise UnprovenApi("entry-point name and descriptor id disagree")
            plugin.openapi_fragment()
            for route in plugin.routes:
                reader.handler(route.handler)
        except (
            UnprovenApi,
            ApiPluginContractError,
            SyntaxError,
            OSError,
            ValueError,
            TypeError,
            RecursionError,
        ) as exc:
            # Details describe declaration structure only, never runtime data.
            findings.append(ApiFinding(location, 1, f"{name}: {exc}"))
    return findings
