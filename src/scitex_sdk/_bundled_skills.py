"""Read only the SDK's three bundled skill namespaces, without user discovery."""

from __future__ import annotations

from importlib.resources import files

_NAMESPACES = {
    "scitex-sdk": ("_skills", "scitex-sdk"),
    "scitex-app": ("app", "_skills", "scitex-app"),
    "scitex-ui": ("ui", "_skills", "scitex-ui"),
}


def list_bundled_skills() -> dict[str, list[str]]:
    """Return relative Markdown skill IDs grouped by their bundled namespace.

    This reads only installed package resources. It never consults HOME,
    environment configuration, plugin discovery, installed user skills or a
    workspace, and it returns no filesystem paths. SKILL.md is the index and
    is excluded, matching the existing app/UI CLI and MCP list operations.
    """
    package = files("scitex_sdk")
    result = {}
    for namespace, parts in _NAMESPACES.items():
        root = package
        for part in parts:
            root = root.joinpath(part)
            if getattr(root, "is_symlink", lambda: False)():
                raise ValueError(
                    "SDK bundled skill namespaces must not contain aliases"
                )
        if not root.is_dir():
            raise FileNotFoundError("SDK bundled skill namespace is missing")
        pending = [(root, "", 0)]
        names = []
        visited = 0
        while pending:
            directory, prefix, depth = pending.pop()
            if depth > 8:
                raise RuntimeError("SDK bundled skill nesting limit exceeded")
            for resource in directory.iterdir():
                visited += 1
                if visited > 4096:
                    raise RuntimeError("SDK bundled skill entry limit exceeded")
                if getattr(resource, "is_symlink", lambda: False)():
                    raise ValueError("SDK bundled skills must not contain aliases")
                relative = prefix + resource.name
                if resource.is_dir():
                    pending.append((resource, relative + "/", depth + 1))
                elif (
                    resource.is_file()
                    and resource.name.endswith(".md")
                    and resource.name != "SKILL.md"
                ):
                    names.append(relative[:-3])
        result[namespace] = sorted(names)
    return result
