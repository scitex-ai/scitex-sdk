---
description: |
  [TOPIC] Files SDK
  [DETAILS] Core file operations SDK — get_files(), FilesBackend protocol, FileSystemBackend, build_tree(). Write-once API for local and cloud storage..
tags: [scitex-app-files-sdk]
---

# Files SDK

Write-once file I/O that auto-routes to local filesystem or cloud backend.

## get_files()

```python
def get_files(
    root: Optional[Union[str, Path]] = None,
    *,
    backend: Optional[str] = None,
    **kwargs,
) -> FilesBackend
```

Auto-detection order:
1. `backend` kwarg specified → use that registered backend
2. `SCITEX_API_TOKEN` env set → use "cloud" backend (auto-registers if needed)
3. Otherwise → `FileSystemBackend(root or cwd)`

```python
from scitex_sdk.app.sdk import get_files

# Explicit local storage, even if an API token is inherited
files = get_files("./my_project", backend="local")

# Cloud (SCITEX_API_TOKEN must be set)
files = get_files()

# Explicit backend
files = get_files(backend="s3", bucket="my-bucket")
```

`root` alone does not select local storage: a nonempty token still selects
cloud, where the built-in factory treats `root` as an app namespace, not a
filesystem directory. `SCITEX_API_URL` alone does not select cloud.

Explicit names must already be registered. The built-in `local` and
`filesystem` names are registered at import time; a host can replace any
registered factory. Explicit `backend="cloud"` raises `KeyError` until that
name has been registered; token-based automatic selection registers the
built-in factory when needed. Backend construction makes no HTTP request and
is not proof of credentials, permissions or server availability.

The App MCP file tools use a different default: `backend="local"` pins local
storage. Their explicit `backend="cloud"` route requires a nonempty token and
registers the cloud factory; it refuses a missing token instead of falling
back. See `app/_mcp/server.py::_resolve_files`.

Owner and behavioral evidence: `app/sdk/__init__.py::get_files`,
`app/sdk/_cloud_files.py::cloud_files_factory`,
`tests/scitex_sdk/app/sdk/test___init___files_local.py` and
`tests/scitex_sdk/app/_mcp/test_server.py`.

## FilesBackend Protocol

Structural protocol (`typing.Protocol`) — backends implement these 7 methods without subclassing:

```python
class FilesBackend(Protocol):
    def read(self, path: str, *, binary: bool = False) -> Union[str, bytes]: ...
    def write(self, path: str, content: Union[str, bytes]) -> None: ...
    def list(self, directory: str = "", *, extensions: Optional[List[str]] = None) -> List[str]: ...
    def exists(self, path: str) -> bool: ...
    def delete(self, path: str) -> None: ...
    def rename(self, old_path: str, new_path: str) -> None: ...
    def copy(self, src_path: str, dest_path: str) -> None: ...
```

All `path` arguments are relative to the backend's root namespace.
`FileSystemBackend` resolves paths and refuses escapes from its root (including
symlink escapes); see `tests/scitex_sdk/app/sdk/test__filesystem.py`.
Cloud paths are forwarded to the service; this client does not establish
server-side traversal protection or authorization.

### read()

```python
content = files.read("data/config.yaml")          # str (UTF-8)
data    = files.read("data/model.pt", binary=True) # bytes
```

Raises `FileNotFoundError` if path does not exist.

### write()

```python
files.write("output/result.csv", csv_text)         # str content
files.write("output/model.pt", model_bytes)        # bytes content
```

Creates parent directories automatically.

### list()

```python
all_files  = files.list()                              # all in root
yaml_files = files.list("config", extensions=[".yaml"])
py_files   = files.list("src", extensions=[".py"])
```

Returns list of relative path strings. Only files, not directories.

### exists() / delete() / rename() / copy()

```python
if files.exists("data/config.yaml"):
    files.delete("data/old.csv")

files.rename("output/draft.txt", "output/final.txt")  # raises FileExistsError if dest exists
files.copy("templates/base.html", "output/base.html")
```

## register_backend()

```python
def register_backend(name: str, factory: Callable[..., FilesBackend]) -> None
```

Register a custom backend factory:

```python
from scitex_sdk.app.sdk import register_backend

def my_s3_factory(root, *, bucket, **kwargs):
    return MyS3Backend(bucket=bucket, prefix=root)

register_backend("s3", my_s3_factory)
files = get_files(backend="s3", bucket="my-bucket")
```

## FileSystemBackend

Local-disk implementation included with scitex-app. Path traversal outside root is blocked.

```python
from scitex_sdk.app.sdk._filesystem import FileSystemBackend

fs = FileSystemBackend("/path/to/root")
print(fs.root)   # Path("/path/to/root")
print(repr(fs))  # FileSystemBackend(/path/to/root)
```

## build_tree()

```python
def build_tree(
    backend: FilesBackend,
    directory: str = "",
    *,
    extensions: Optional[List[str]] = None,
    skip_hidden: bool = True,
    max_depth: int = 10,
) -> List[Dict[str, Any]]
```

Builds a nested tree structure for file browser UIs.

```python
from scitex_sdk.app import build_tree
from scitex_sdk.app.sdk import get_files

files = get_files("./project")
tree = build_tree(files, extensions=[".yaml", ".json"], max_depth=3)
# [
#   {"path": "config", "name": "config", "type": "directory",
#    "children": [
#      {"path": "config/settings.yaml", "name": "settings.yaml", "type": "file"}
#    ]},
#   {"path": "README.md", "name": "README.md", "type": "file"},
# ]
```

Only non-empty directories are included. Hidden files (`.gitignore`, etc.) are skipped by default. Results are sorted case-insensitively.
