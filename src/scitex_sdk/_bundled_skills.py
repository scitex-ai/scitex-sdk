"""Read only the SDK's three bundled skill namespaces, without user discovery."""

from __future__ import annotations

from importlib.resources import files

_NAMESPACES = {
    "scitex-sdk": ("_skills", "scitex-sdk"),
    "scitex-app": ("app", "_skills", "scitex-app"),
    "scitex-ui": ("ui", "_skills", "scitex-ui"),
}


def _namespace_root(namespace: str):
    root = files("scitex_sdk")
    for part in _NAMESPACES[namespace]:
        root = root.joinpath(part)
        if getattr(root, "is_symlink", lambda: False)():
            raise ValueError("SDK bundled skill namespaces must not contain aliases")
    if not root.is_dir():
        raise FileNotFoundError("SDK bundled skill namespace is missing")
    return root


def read_bundled_skill(namespace: str, name: str) -> str:
    """Read an exact bundled skill ID, or SKILL for its namespace overview.

    Use the same bounded catalog as discovery, without user/plugin lookup.
    Absolute paths, traversal, backslashes and aliases are never admitted.
    """
    if (
        not isinstance(name, str)
        or "\\" in name
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        raise ValueError("skill name must stay inside its bundled catalog")
    catalog = list_bundled_skills()[namespace]
    if name != "SKILL" and name not in catalog:
        raise FileNotFoundError(f"unknown skill {name!r}; available: {catalog}")
    resource = _namespace_root(namespace)
    for part in (name + ".md").split("/"):
        resource = resource.joinpath(part)
        if getattr(resource, "is_symlink", lambda: False)():
            raise ValueError("SDK bundled skills must not contain aliases")
    if not resource.is_file():
        raise FileNotFoundError(f"unknown skill {name!r}")
    return resource.read_text(encoding="utf-8")


def list_bundled_skills() -> dict[str, list[str]]:
    """Return relative Markdown skill IDs grouped by their bundled namespace.

    This reads only installed package resources. It never consults HOME,
    environment configuration, plugin discovery, installed user skills or a
    workspace, and it returns no filesystem paths. SKILL.md is the index and
    is excluded, matching the existing app/UI CLI and MCP list operations.
    """
    result = {}
    for namespace in _NAMESPACES:
        root = _namespace_root(namespace)
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
