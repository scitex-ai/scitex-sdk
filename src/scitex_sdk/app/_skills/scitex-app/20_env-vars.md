---
description: |
  [TOPIC] Environment Variables
  [DETAILS] Selected environment variables used by scitex-sdk app — storage, cloud API, standalone Django, and LLM configuration..
tags: [scitex-app-env-vars]
---

# Environment Variables

## Storage and Path Resolution

| Variable | Purpose | Used by |
|----------|---------|---------|
| `SCITEX_DIR` | Relocate the user-scope `.scitex/` tree | `scitex_sdk.app._cli._skills._scitex_dir()` |
| `SCITEX_BASE_DIR` | Base directory for app path resolution | `scitex_sdk.app.paths.get_base_dir()` |
| `SCITEX_WORKING_DIR` | Working directory for standalone file tree | `run_standalone()` |

```bash
export SCITEX_BASE_DIR=/data/scitex
export SCITEX_WORKING_DIR=/home/user/projects
```

## Cloud API

| Variable | Purpose | Default |
|----------|---------|---------|
| `SCITEX_API_TOKEN` | JWT token for cloud API authentication | — |
| `SCITEX_API_URL` | Cloud API base URL | `http://127.0.0.1:8000` |
| `SCITEX_SERVER_URL` | Server URL for `app install-dev` and `app submit` | `http://127.0.0.1:8000` |

A nonempty `SCITEX_API_TOKEN` selects cloud only when `get_files()` has no
explicit backend. Passing a directory as `root` does not override this.
Use `get_files("./project", backend="local")` to pin the built-in filesystem
backend, even when a token is inherited. `SCITEX_API_URL` configures the HTTP
client endpoint; setting it alone does not select cloud. `SCITEX_SERVER_URL`
belongs to the install/submit CLI options, not the files client.

The built-in client takes nonempty explicit `token`/`base_url` constructor
values before environment values, strips trailing URL slashes, and otherwise
uses the URL default above. Its lazy singleton captures those values at first
use; later environment changes do not update an existing client. This is an
internal implementation detail, not a new public client API.

Owner: `app/sdk/__init__.py::get_files`, `app/sdk/_client.py::PlatformClient`
and `get_client`, and `app/_cli/_app.py` Click options.
See [Files SDK](19_files-sdk.md) for registration and MCP differences.

```bash
export SCITEX_API_TOKEN="eyJhbGci..."
export SCITEX_API_URL="https://scitex.ai"
export SCITEX_SERVER_URL="https://scitex.example.com"
```

## Standalone Django

| Variable | Purpose | Default |
|----------|---------|---------|
| `DJANGO_SECRET_KEY` | Django secret key for standalone mode | `"scitex-standalone-dev-key"` |
| `DJANGO_DEBUG` | True only when the lowercased value equals `"true"` | `"true"` |
| `SCITEX_ALLOWED_HOSTS` | Additional comma-separated allowed hostnames | empty |

```bash
export DJANGO_SECRET_KEY="your-local-development-secret-key"
export DJANGO_DEBUG="false"
```

These settings are read only when `_configure_django()` configures fresh
settings. An already-configured embedding host retains its own secret, debug,
host and static settings. The SDK shell is bundled as `scitex_sdk.ui`.
`SCITEX_UI_STATIC` has no reader in this launcher; use the explicit
`extra_staticfiles_dirs` argument for additional static directories instead.

`working_dir` sets the resolved `SCITEX_WORKING_DIR`; otherwise an existing
environment value is retained, then the current directory is used. The later
`extra_env` overlay can override it. See [Standalone Mode](05_standalone.md).

Owner: `app/_standalone.py::run_standalone` and `_configure_django`.
Fresh-settings/host-preservation and no-bind server-option controls live in
`tests/scitex_sdk/app/test__standalone_scitex_ui_guard.py`; hostname controls
live in `test__standalone_allowed_hosts.py`.

## LLM / Chat

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | API key for Anthropic chat backend | — |
| `SCITEX_APP_LLM_MODEL` | LLM model identifier for chat features | `anthropic/claude-sonnet-4-20250514` |

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SCITEX_APP_LLM_MODEL="anthropic/claude-opus-4-5"
```

The unprefixed `LLM_MODEL` still works and logs a deprecation warning. Rename
it — the generic name can collide with another tool in the same environment,
which would silently change which model you talk to. If both are set they are
not merged: the prefixed one wins and the conflict is logged, so the pick is
never silent.

The intended model-environment contract above is currently implemented by
`_resolve_default_model()` on the LiteLLM selection path. The direct Anthropic
selection path in `app/_chat/_backends.py::get_chat_backend` currently uses its
hard-coded default when the explicit `model` argument is absent; it bypasses
both environment names and their conflict warning. This remains an
implementation gap, not a supported exception to the intended contract.
An explicit `get_chat_backend(model=...)` value takes priority on either path.
The existing `tests/scitex_sdk/app/_chat/test__backends.py` controls test the
resolver itself; they do not establish that every backend selection uses it.

## Usage Examples

### Local development (default)

`get_files("./project", backend="local")` selects the built-in filesystem
backend regardless of an inherited API token. Without an explicit backend,
local is the default only when the token is absent or empty.

### Cloud-connected development

```bash
export SCITEX_API_TOKEN="your-jwt-token"
export SCITEX_API_URL="https://scitex.ai"
```

Then `get_files()` selects the cloud backend, registering its built-in factory
if necessary. Selection does not contact the server or validate the token;
a later file operation performs the HTTP request.

### Remote local server

```bash
export SCITEX_API_TOKEN="your-jwt-token"
export SCITEX_API_URL="http://192.168.1.100:8000"
```

### Local standalone development with debug disabled

```bash
export DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(50))')"
export DJANGO_DEBUG="false"
export SCITEX_WORKING_DIR="/data/user_projects"
```

These environment settings still launch Django’s development server. They do
not constitute a production deployment configuration.
