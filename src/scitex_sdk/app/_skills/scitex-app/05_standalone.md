---
description: |
  [TOPIC] Standalone Mode
  [DETAILS] run_standalone() — launch a SciTeX app locally with the full workspace shell (Django + sidebar + file tree + AI panel) without scitex-hub..
tags: [scitex-app-standalone]
---

# Standalone Mode

`scitex_sdk.app.embed.run_standalone()` starts a local Django development
server with the SDK workspace shell. It does not require a SciTeX Hub server.

`embed` is the public host-embedding surface (`scitex_sdk.app.embed`) — import from there, not from the private `scitex_sdk.app._standalone` / `scitex_sdk.app._django` implementation modules.

## run_standalone()

```python
def run_standalone(
    app_module: str,
    port: int = 8050,
    host: str = "127.0.0.1",
    open_browser: bool = True,
    hot_reload: bool = False,
    working_dir: Optional[str] = None,
    desktop: bool = False,
    extra_installed_apps: Optional[list[str]] = None,
    extra_staticfiles_dirs: Optional[list[str]] = None,
    extra_env: Optional[dict[str, str]] = None,
) -> None: ...
```

### Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `app_module` | required | Dotted path to the app's Django module (e.g. `"my_app"`) |
| `port` | `8050` | TCP port for the Django server |
| `host` | `"127.0.0.1"` | Host to bind (use `"0.0.0.0"` for LAN access) |
| `open_browser` | `True` | Open browser tab automatically after 1.5 s |
| `hot_reload` | `False` | Enable the Django autoreloader (file watching) |
| `working_dir` | `None` | Sets the resolved `SCITEX_WORKING_DIR`; otherwise retains an existing value, then falls back to `cwd` |
| `desktop` | `False` | Launch as native window via `pywebview` if installed |
| `extra_installed_apps` | `None` | Additional Django app strings to add to `INSTALLED_APPS` |
| `extra_staticfiles_dirs` | `None` | Additional static file directories |
| `extra_env` | `None` | Extra env vars to set before Django configures |

### Basic usage

```python
from scitex_sdk.app.embed import run_standalone

# Minimal — app at my_app/urls.py, my_app/views.py, etc.
run_standalone(app_module="my_app")

# Custom port, no browser
run_standalone(app_module="my_app", port=8051, open_browser=False)

# Native desktop window (requires: pip install pywebview)
run_standalone(app_module="my_app", desktop=True)
```

### From a scaffolded app's CLI

Apps created with `scitex-sdk app init` get a `_cli.py` with a `gui` command:

```bash
my-app gui                           # default port 8050
my-app gui --port 8051 --no-browser
my-app gui --force                   # stop THIS app's own previous instance, then serve
```

The `gui` command uses `scitex_sdk.app.embed.serve_gui`: it binds exactly
`--port` or fails loud (never drifts to the next free port), and refuses
a second instance of this app's own GUI unless `--force` is given.

`--force` stops this app's own GUI whether it is *recorded* in the
runtime state or *orphaned* — still holding the port after dying without
clearing that state, which is exactly the case the flag exists for.
It never touches a process it cannot prove is ours, and ownership is
proven from the holder's **argv**, not its name: a `comm` of `python`
is shared by every Python server on the box.

For a foreign holder it prints the name, pid and argv with a `kill`
command, and never offers `--force` — a remedy that would refuse.
When the port is held but the holder cannot be identified (our agent
containers deny `/proc/<pid>/fd` even for our own processes), it says
so plainly rather than blaming another user. The three outcomes are
declared on `PortHolder.status`: `free`, `identified`, `unreadable`;
`ours` is three-valued — `True`, `False`, or `None` for "we could not
look".

### Django settings configured

The following settings apply only when Django settings are not already
configured. `_configure_django()` returns immediately when
`django.conf.settings.configured` is true, so an embedding host keeps its own
settings. Setting `DJANGO_SETTINGS_MODULE` alone is not the guard: the helper
checks the settings object's configured state.

Selected settings for a fresh standalone process:

- `INSTALLED_APPS`: `django.contrib.staticfiles`, `scitex_sdk.app`,
  `<app_module>` and the bundled `scitex_sdk.ui`, followed by explicit
  `extra_installed_apps` entries. These are SDK modules, not separate legacy
  `scitex-app` or `scitex-ui` installations. The launcher raises
  `ScitexUiRequiredError` before configuration if the SDK UI module is missing.
- `ROOT_URLCONF`: `<app_module>.urls`; `STATIC_URL`: `/static/`.
- `STATICFILES_DIRS`: the app's existing `static/` directory, the existing
  `_standalone_static/` directory if present, and `extra_staticfiles_dirs`.
  Django also discovers installed apps' static assets.
- `DATABASES`: `{}`. Read-only apps and chat streaming can run without a
  database; session history has additional requirements below.
- `SECRET_KEY`: `DJANGO_SECRET_KEY`, or `scitex-standalone-dev-key` when absent.
- `DEBUG`: true only when `DJANGO_DEBUG.lower() == "true"`; the default is
  `"true"`. `"1"` and `"true "` are false.
- `ALLOWED_HOSTS`: loopback, names implied by the bound `host`, and
  comma-separated `SCITEX_ALLOWED_HOSTS` entries.
- `SCITEX_APP_MODE`: `"standalone"`; the project provider is
  `scitex_sdk.app.project_context.StandaloneProjectProvider`.

The settings helper configures only once. Calling `run_standalone()` again is
not a no-op: it still applies its environment updates and reaches server
startup. `working_dir` first sets a resolved `SCITEX_WORKING_DIR`; when omitted,
an existing value is retained, otherwise the current directory is used.
`extra_env` is applied afterward and can override that value.

`DJANGO_DEBUG=false` does not turn this launcher into a production server.
`_run_server()` invokes Django's development `runserver` with `--insecure` to
serve static assets, and adds `--noreload` when `hot_reload=False`. Use the
host's deployment settings and server for production hosting.

Owning implementation: `app/_standalone.py::run_standalone`,
`_configure_django` and `_run_server`; public aliases live in `app/embed.py`.
Behavioral controls: `tests/scitex_sdk/app/test__standalone_scitex_ui_guard.py`,
`test__standalone_allowed_hosts.py` and `test_embed.py`. The fresh-settings
controls exercise real Django configuration and stop the server before bind;
they do not establish a live deployment or rendered UI acceptance.

### Chat, in a profile with no database

`DATABASES: {}` above is not a detail — it decides which chat routes you may
mount. There are two mount points and they are not interchangeable:

```python
urlpatterns += chat.chat_stream_urlpatterns   # streaming only, NO database
urlpatterns += chat.chat_urlpatterns          # + session history, needs one
```

`chat_urlpatterns` bundles session CRUD routes that need the ORM. Without a
usable database they raise `chat.ChatSessionsRequireADatabaseError`; with a
database but no registered models app they raise
`chat.ChatSessionsAppNotInstalledError`. Unhandled, these are server errors.
Use `chat_stream_urlpatterns` for the launcher’s database-free settings.

Session history requires both a usable database and the models’ app registered.
Catch `chat.ChatSessionsUnavailableError` when a host needs to handle either
missing prerequisite; its subclasses distinguish the required fixes.
Behavioral controls live in
`tests/scitex_sdk/app/_chat/test__django_mount_points.py`,
`test__django_db_free.py`, `test__session_views_database_guard.py` and
`test__session_views_app_registration.py`.

### Requirements

- `scitex-sdk[gui]` supplies the Django dependencies; the UI shell is bundled
  as `scitex_sdk.ui` and required by this launcher
- `pywebview` (optional, only for `desktop=True`)

### Testing the `gui` command's real CLI path

`serve_gui`'s state-file location can be redirected with an env var --
the only channel available to a subprocess-driven end-to-end test
(`python -m my_app gui serve` run as a real subprocess), which cannot
inject a path via function arguments across a process boundary. Set
`SCITEX_<PACKAGE>_GUI_STATE` (package name uppercased, non-alnum chars
-> `_`, e.g. `SCITEX_MY_APP_GUI_STATE` for `"my-app"`) before spawning
the subprocess to point state at a tmp path instead of the developer's
real runtime state -- keeps end-to-end CLI tests mock-free.

## CSRF in fresh standalone settings

The shared launcher includes Django's `CsrfViewMiddleware` when it creates
fresh standalone settings. Unsafe GUI requests need the normal token/origin
checks; the SDK creator sends the token rendered in its page. A successful
page load or input-validation call does not authorize creation or publication.
An already configured host keeps its own middleware and security settings;
the launcher does not add or replace them.

Owner: `app/_standalone.py::_configure_django`. Real fresh-settings controls in
`tests/integration/test_standalone_csrf.py` verify a missing token returns403,
a rendered token permits the input-validation request, and an explicitly
configured host's middleware is preserved. These checks do not establish
hosted authentication, project authorization or a package-wide API policy.
