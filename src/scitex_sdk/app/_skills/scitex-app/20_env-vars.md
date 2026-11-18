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

`app/_chat/_backends.py::get_chat_backend` uses this resolver on both the
direct Anthropic and LiteLLM selection paths when no nonempty explicit model
is supplied. The direct Anthropic client expects a bare model ID: an optional
leading `anthropic/` is removed from the resolved environment value. LiteLLM
retains the provider-qualified value. Backend priority remains direct
Anthropic when its SDK and a nonempty `ANTHROPIC_API_KEY` are available;
changing the model environment variable does not change that priority.

A nonempty explicit `get_chat_backend(model=...)` value takes priority on
either path, is forwarded unchanged, and bypasses the environment resolver
and its warnings. Use a bare Anthropic ID for an explicit direct-client model.
A per-request `backend.stream(..., model=...)` value also retains its existing
priority over the backend's default model.

Behavioral controls: `tests/scitex_sdk/app/_chat/test__backends.py` exercises
resolver precedence and warnings.
`tests/integration/test_chat_backend_model_selection.py` exercises
actual factory selection and the real Anthropic client against an owned
loopback SSE endpoint, checking wire model IDs, warnings and streamed events;
external connections are blocked. These controls do not call a hosted model
or establish provider availability or acceptance of a particular model ID.

### Anthropic sampling compatibility

The direct Anthropic backend retains its historical `temperature=0.7`
compatibility default without sending a sampling parameter. That value is not
a sampling control on this path. A non-default value, including `0.0`, is sent
only when the installed SDK's `messages.stream` explicitly exposes the
`temperature` parameter. Otherwise the backend returns an error event before
making a request; it does not silently ignore the custom value or force an
unsupported field into the request body.

Anthropic SDK 2.10.0 does not expose this parameter; the
[upstream migration guide](https://github.com/anthropics/anthropic-sdk-python/blob/main/MIGRATION.md)
records its removal. Do not infer hosted API/model support from an older SDK
accepting the argument. LiteLLM forwarding is unchanged, with support decided
by its provider. Migrating the shared historical default to a distinct
omitted-value contract remains separate interface work.

The same integration test covers non-default, zero and compatibility-default
temperatures through the actual installed provider SDK, and checks that a
local refusal makes no HTTP request. `max_tokens` and `system` keep their
existing forwarding behavior.

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
