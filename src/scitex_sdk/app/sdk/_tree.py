#!/usr/bin/env python3
# Timestamp: 2026-03-15
# File: scitex_sdk/app/sdk/_tree.py

"""Tree builder utility for FilesBackend.

Converts flat file listings into nested directory tree structures.
Reusable by any app that needs a file browser UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


def build_tree(
    backend: Any,
    directory: str = "",
    *,
    extensions: Optional[List[str]] = None,
    skip_hidden: bool = True,
    max_depth: int = 10,
) -> List[Dict[str, Any]]:
    """Build a nested tree structure from a FilesBackend.

    Parameters
    ----------
    backend : FilesBackend
        A file storage backend implementing the FilesBackend protocol.
    directory : str
        Starting directory (relative to backend root). Default: root.
    extensions : list of str, optional
        Filter files by extension (e.g., [".yaml", ".png"]).
        Directories are always included for traversal.
    skip_hidden : bool
        Skip files/directories starting with ".". Default: True.
    max_depth : int
        Maximum recursion depth to prevent runaway traversal. Default: 10.

    Returns
    -------
    list of dict
        Nested tree structure::

            [
                {"path": "subdir", "name": "subdir", "type": "directory",
                 "children": [...]},
                {"path": "file.yaml", "name": "file.yaml", "type": "file"},
            ]
    """
    if max_depth <= 0:
        return []

    # Get all entries in this directory
    entries = _list_entries(backend, directory)
    items = []

    for entry in entries:
        name = Path(entry["path"]).name

        if skip_hidden and name.startswith("."):
            continue

        if entry["type"] == "directory":
            try:
                children = build_tree(
                    backend,
                    entry["path"],
                    extensions=extensions,
                    skip_hidden=skip_hidden,
                    max_depth=max_depth - 1,
                )
            except (PermissionError, ValueError):
                # Skip unreadable directories AND outward children refused by
                # backend containment; valid sibling entries are kept. An
                # explicitly escaping top-level `directory` still raises from
                # _list_entries above — it is a caller error, not a child.
                continue
            if children:  # only include non-empty directories
                items.append(
                    {
                        "path": entry["path"],
                        "name": name,
                        "type": "directory",
                        "children": children,
                    }
                )
        else:
            # Apply extension filter to files
            if extensions:
                suffix = Path(name).suffix.lower()
                if suffix not in extensions:
                    continue
            items.append(
                {
                    "path": entry["path"],
                    "name": name,
                    "type": "file",
                }
            )

    # Sort: pure alphabetical (case-insensitive), dirs and files interleaved
    items.sort(key=lambda x: x["name"].lower())
    return items


def _list_entries(
    backend: Any,
    directory: str = "",
) -> List[Dict[str, str]]:
    """List directory entries with type information.

    Tries backend.list_entries() first (if available, returns files + dirs).
    Falls back to backend.list() for files and attempts directory discovery.
    """
    # Preferred: backend supports list_entries() returning typed entries
    if hasattr(backend, "list_entries"):
        return backend.list_entries(directory)

    # Fallback: use list() for files, try to discover directories
    # via the backend's internal structure
    if hasattr(backend, "_root"):
        # FileSystemBackend — guard AND enumerate the SAME physical target:
        # validate through the backend's own containment (component
        # comparison, not string prefix) and iterate the validated result, so
        # the guarded path and the enumerated path can never differ (a
        # lexical normpath of e.g. "alias/../.." could point outside while
        # the resolved target is valid, or vice versa). Returned metadata is
        # built from the original logical request plus child name, so the
        # alias namespace is preserved instead of the real path. A symlink
        # child pointing outside is still LISTED by name (its link path is
        # inside root) but any read through it hits the same refusal —
        # listing names is not operating on targets.
        _resolve = getattr(backend, "_resolve", None)
        root = backend._root
        if directory and _resolve is not None:
            target = _resolve(directory)  # raises on escape
            logical_base = directory
        else:
            target = (root / directory) if directory else root
            logical_base = None
        if not target.is_dir():
            return []
        entries = []
        try:
            children = sorted(target.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            return []
        for item in children:
            try:
                if logical_base is not None:
                    rel = str(Path(logical_base) / item.name)
                else:
                    rel = str(item.relative_to(root))
                if item.is_dir():
                    entries.append({"path": rel, "type": "directory"})
                elif item.is_file():
                    entries.append({"path": rel, "type": "file"})
            except PermissionError:
                continue  # skip files/dirs we can't access
        return entries

    # Last resort: list() returns only files, no directory info
    files = backend.list(directory)
    return [{"path": f, "type": "file"} for f in files]


# EOF
