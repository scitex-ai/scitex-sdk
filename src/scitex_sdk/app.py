"""scitex_sdk.app — the app contract (facade over ``scitex_app``).

Step 1 re-exports the documented public surface of ``scitex_app`` by IDENTITY
(the same function/class/submodule objects), so ``from scitex_sdk.app import
get_files`` is the same object as ``from scitex_app import get_files``. The
implementation moves here gradually after the facade releases.
"""

from __future__ import annotations

from scitex_app import (
    FilesBackend,
    build_tree,
    chat,
    copy_file,
    delete_file,
    embed,
    file_exists,
    get_files,
    hosts_to_allow,
    list_files,
    paths,
    read_file,
    register_backend,
    rename_file,
    scaffold,
    validate,
    validator,
    write_file,
)

__version__ = "0.1.0"  # facade version; the app contract's own version is scitex_app.__version__

__all__ = [
    "FilesBackend",
    "build_tree",
    "chat",
    "copy_file",
    "delete_file",
    "embed",
    "file_exists",
    "get_files",
    "hosts_to_allow",
    "list_files",
    "paths",
    "read_file",
    "register_backend",
    "rename_file",
    "scaffold",
    "validate",
    "validator",
    "write_file",
    "__version__",
]
