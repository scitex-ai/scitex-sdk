#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``scitex-sdk gui {serve,open,status,stop}`` — the SciTeX SDK wizard GUI.

The ecosystem-standard GUI verbs (matching sac, scitex-cards,
scitex-storage): ``serve`` runs the wizard in the foreground,
``open`` auto-serves detached then opens a browser, ``status``/``stop``
inspect the runtime state. A bare ``scitex-sdk gui`` hard-errors with a
redirect rather than guessing (noun-verb contract).

Importing this module needs only ``click``, never Django, so
``scitex-sdk --help`` always lists ``gui``. ``serve``/``open`` boot the
wizard through the engine's launcher (``scitex_sdk.app.embed``) until the
implementation consolidates into the SDK.
"""

from __future__ import annotations

import importlib.metadata
import json
import copy
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click

PACKAGE = "scitex-sdk"


def _installed_version() -> str:
    try:
        return importlib.metadata.version(PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        from scitex_sdk import __version__ as src_version

        return src_version


SDK_VERSION = _installed_version()

DEFAULT_PORT = 31301
DEFAULT_HOST = "127.0.0.1"


def _gui_status():
    from scitex_sdk.app.embed import gui_status

    return gui_status(PACKAGE)


def _gui_stop():
    from scitex_sdk.app.embed import gui_stop

    return gui_stop(PACKAGE)


def _guard_bind(host: str, allow_remote: bool) -> None:
    if host in {"127.0.0.1", "localhost", "::1"} or allow_remote:
        return
    raise click.ClickException(
        f"Refusing non-loopback bind {host!r}: the wizard scaffolds files on "
        "this machine. Pass --allow-remote only behind trusted access "
        "or an authenticated proxy."
    )


def _log_path() -> Path:
    from scitex_config._ecosystem import local_state

    return Path(local_state.runtime_path(PACKAGE, "gui-serve.log"))


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(SDK_VERSION, "-V", "--version", prog_name="scitex-sdk")
@click.option(
    "--help-recursive",
    is_flag=True,
    default=False,
    help="Show help for all commands.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit structured JSON output (propagates to subcommands that honour it).",
)
@click.pass_context
def main(
    ctx: click.Context, help_recursive: bool, as_json: bool
) -> None:
    """scitex-sdk (vX.Y.Z) — app contract + UI shell + SciTeX SDK wizard.

    Config is loaded per component group with the SciTeX precedence chain:
    config.yaml -> $SCITEX_<GROUP>_CONFIG -> ~/.scitex/<group>/config.yaml
    -> defaults (see `scitex-sdk app --help` and `scitex-sdk ui --help`).
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    if help_recursive:
        _print_help_recursive(ctx)
        ctx.exit(0)
    if ctx.invoked_subcommand is not None:
        return
    click.echo(ctx.get_help())


main.help = main.help.replace("(vX.Y.Z)", f"(v{SDK_VERSION})")


def _print_help_recursive(ctx: click.Context) -> None:
    """Print help for the root and every subcommand, depth-first."""
    click.secho("=== scitex-sdk ===", fg="cyan", bold=True)
    click.echo(ctx.get_help())
    for name in sorted(main.list_commands(ctx) or []):
        cmd = main.get_command(ctx, name)
        if cmd is None:
            continue
        click.echo()
        click.secho(f"=== scitex-sdk {name} ===", fg="cyan", bold=True)
        sub = click.Context(cmd, info_name=name, parent=ctx)
        click.echo(cmd.get_help(sub))
        if isinstance(cmd, click.Group):
            for sub_name in sorted(cmd.list_commands(sub) or []):
                sub_cmd = cmd.get_command(sub, sub_name)
                if sub_cmd is None:
                    continue
                click.echo()
                click.secho(
                    f"=== scitex-sdk {name} {sub_name} ===", fg="cyan", bold=True
                )
                with click.Context(
                    sub_cmd, info_name=sub_name, parent=sub
                ) as sub_sub:
                    click.echo(sub_cmd.get_help(sub_sub))


@main.group("gui", invoke_without_command=True)
@click.pass_context
def gui(ctx: click.Context) -> None:
    """Serve the SciTeX SDK wizard (open/serve/status/stop)."""
    if ctx.invoked_subcommand is not None:
        return
    click.echo(
        "ERROR: `scitex-sdk gui` needs a verb. Use:\n"
        "  scitex-sdk gui serve [--port N] [--host H]  # foreground/blocking\n"
        "  scitex-sdk gui open                        # serve + open a browser\n"
        "  scitex-sdk gui status [--json]\n"
        "  scitex-sdk gui stop --yes",
        err=True,
    )
    ctx.exit(2)


@gui.command("serve")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int)
@click.option("--host", default=DEFAULT_HOST, show_default=True)
@click.option("--allow-remote", is_flag=True, help="Allow a non-loopback bind.")
@click.option("--force", is_flag=True, help="Reclaim a previous creator GUI instance.")
@click.option("--hot-reload", is_flag=True, help="Enable Django auto-reload.")
@click.option("--dry-run", is_flag=True, help="Print the launch without starting it.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def gui_serve(
    port: int,
    host: str,
    allow_remote: bool,
    force: bool,
    hot_reload: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Run the SciTeX SDK wizard in the foreground (blocking, headless).

    \b
    Example:
      $ scitex-sdk gui serve --port 31301
      $ scitex-sdk gui serve --dry-run
    """
    _guard_bind(host, allow_remote)
    if dry_run:
        payload = {"would_serve": True, "host": host, "port": port, "force": force}
        click.echo(
            json.dumps(payload) if as_json else f"Would serve at http://{host}:{port}"
        )
        return
    try:
        import django  # noqa: F401
    except ImportError as exc:
        raise click.ClickException(
            "The SciTeX SDK GUI requires Django. Install with: "
            f"pip install 'scitex-sdk[gui]'  ({exc})"
        ) from exc
    from scitex_sdk.creator._server import serve

    exit_code = serve(
        package=PACKAGE,
        project_dir=os.getcwd(),
        port=port,
        host=host,
        force=force,
        hot_reload=hot_reload,
    )
    if exit_code:
        raise click.exceptions.Exit(exit_code)


@gui.command("open")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int)
@click.option("--host", default=DEFAULT_HOST, show_default=True)
@click.option("--allow-remote", is_flag=True, help="Allow a non-loopback bind.")
@click.option("--no-browser", is_flag=True, help="Start the server but do not open a tab.")
@click.option("--dry-run", is_flag=True, help="Print the launch without starting it.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def gui_open(
    port: int,
    host: str,
    allow_remote: bool,
    no_browser: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Open the wizard, starting a detached server when necessary.

    \b
    Example:
      $ scitex-sdk gui open
      $ scitex-sdk gui open --no-browser
    """
    _guard_bind(host, allow_remote)
    if dry_run:
        payload = {"would_open": True, "host": host, "port": port}
        click.echo(
            json.dumps(payload) if as_json else f"Would open http://{host}:{port}"
        )
        return
    current = _gui_status()
    if not current.get("running"):
        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-m",
            "scitex_sdk",
            "gui",
            "serve",
            "--port",
            str(port),
            "--host",
            host,
        ]
        if allow_remote:
            command.append("--allow-remote")
        with log_path.open("ab") as log:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            current = _gui_status()
            if current.get("running"):
                break
            time.sleep(0.2)
        else:
            raise click.ClickException(
                f"Wizard did not start within 15 seconds; inspect {log_path}"
            )
    if not no_browser:
        webbrowser.open(current["url"])
    click.echo(
        json.dumps(current) if as_json else f"Wizard running at {current['url']}"
    )


@gui.command("status")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def gui_status(as_json: bool) -> None:
    """Report whether the SciTeX SDK wizard is running.

    \b
    Example:
      $ scitex-sdk gui status
      $ scitex-sdk gui status --json
    """
    current = _gui_status()
    if as_json:
        click.echo(json.dumps(current))
    elif current.get("running"):
        click.echo(f"running at {current['url']} (pid {current.get('pid')})")
    else:
        click.echo("not running")


@gui.command("stop")
@click.option("--dry-run", is_flag=True, help="Print what would be stopped.")
@click.option("--yes", "-y", "yes", is_flag=True, help="Confirm stopping the server.")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def gui_stop(dry_run: bool, yes: bool, as_json: bool) -> None:
    """Stop the SciTeX SDK wizard.

    \b
    Example:
      $ scitex-sdk gui stop --yes
      $ scitex-sdk gui stop --dry-run
    """
    current = _gui_status()
    if not current.get("running"):
        payload = {"running": False, "stopped": False}
        click.echo(json.dumps(payload) if as_json else "not running")
        return
    if dry_run:
        payload = {
            "would_stop": True,
            "pid": current.get("pid"),
            "url": current.get("url"),
        }
        click.echo(json.dumps(payload) if as_json else f"Would stop {current['url']}")
        return
    if not yes:
        raise click.ClickException("Refusing to stop without --yes/-y")
    result = _gui_stop()
    click.echo(json.dumps(result) if as_json else f"stopped (pid {result.get('pid')})")


@main.group("mcp", invoke_without_command=True)
@click.pass_context
def mcp(ctx: click.Context) -> None:
    """MCP (Model Context Protocol) servers for scitex-sdk (app + ui).

    \b
    Example:
      $ scitex-sdk mcp list-tools
      $ scitex-sdk mcp list-tools --json
    """
    if ctx.invoked_subcommand is not None:
        return
    click.echo(ctx.get_help())


@mcp.command("list-tools")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def mcp_list_tools(as_json: bool) -> None:
    """List MCP tools from every scitex-sdk server (app, ui).

    \b
    Example:
      $ scitex-sdk mcp list-tools
      $ scitex-sdk mcp list-tools --json
    """
    import asyncio

    servers: dict[str, object] = {}
    try:
        from scitex_sdk.app._mcp.server import mcp as app_server

        servers["app"] = app_server
    except ImportError as exc:
        raise click.ClickException(
            f"fastmcp not installed. Install with: pip install scitex-sdk[all]\n{exc}"
        ) from exc
    from scitex_sdk.ui._mcp.server import FASTMCP_AVAILABLE, mcp as ui_server

    if not FASTMCP_AVAILABLE:
        raise click.ClickException(
            "fastmcp not installed. Install with: pip install scitex-sdk[all]"
        )
    servers["ui"] = ui_server

    merged: list[dict] = []
    for server_name, server in servers.items():
        tools = asyncio.run(server.list_tools())  # type: ignore[union-attr]
        for tool in tools:
            merged.append(
                {
                    "server": server_name,
                    "name": tool.name,
                    "description": (tool.description or "").splitlines()[0]
                    if tool.description
                    else "",
                }
            )
    if as_json:
        click.echo(json.dumps(merged, indent=2))
        return
    current: str | None = None
    for entry in merged:
        if entry["server"] != current:
            current = entry["server"]
            click.secho(f"[{current}]", fg="cyan", bold=True)
        line = f"  {entry['name']}"
        if entry["description"]:
            line += f" — {entry['description']}"
        click.echo(line)


@main.command("list-python-apis")
@click.option(
    "-v", "--verbose", count=True, help="Verbosity: -v sig+doc1, -vv full doc."
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def list_python_apis(verbose: int, as_json: bool) -> None:
    """List public Python APIs for every scitex-sdk component (app, ui).

    \b
    Example:
      $ scitex-sdk list-python-apis
      $ scitex-sdk list-python-apis --json
    """
    from scitex_sdk import app as scitex_app
    from scitex_sdk import ui as scitex_ui
    from scitex_sdk.app._cli._introspect import _get_api_tree

    merged: list[dict] = []
    for root in (scitex_app, scitex_ui):
        for row in _get_api_tree(root, max_depth=5, docstring=(verbose >= 1)):
            merged.append({"component": root.__name__.split(".")[-1], **row})
    if as_json:
        click.echo(json.dumps(merged, indent=2))
        return
    click.secho(
        f"API tree of scitex-sdk (app + ui, {len(merged)} items):", fg="cyan"
    )
    current: str | None = None
    for row in merged:
        if row["component"] != current:
            current = row["component"]
            click.secho(f"[{current}]", fg="cyan", bold=True)
        click.echo(f"  [{row['Type']}] {row['Name']}")


def _register_components() -> None:
    """Expose owned component CLIs through the canonical SDK command."""
    from scitex_sdk.app._cli import main as component_app
    from scitex_sdk.ui._cli import main as component_ui

    # Compose a separate command tree. Removing a nested group from the
    # imported component itself would change other callers in this process.
    app_commands = copy.copy(component_app)
    app_commands.commands = dict(component_app.commands)
    ui_commands = copy.copy(component_ui)
    ui_commands.commands = dict(component_ui.commands)

    # The previous App executable had a nested `app` development group.
    # Under `scitex-sdk app`, expose its verbs directly.
    development = app_commands.commands.pop("app", None)
    if development is not None:
        for name, command in development.commands.items():
            if name in app_commands.commands:
                raise RuntimeError(f"SDK app command collision: {name}")
            app_commands.add_command(command, name)
    main.add_command(app_commands, "app")
    main.add_command(ui_commands, "ui")

    try:
        from scitex_dev._cli._completion import attach_shell_completion

        attach_shell_completion(main, prog_name="scitex-sdk")
    except Exception:
        pass

    try:
        from scitex_dev.cli import docs_click_group, skills_click_group

        main.add_command(docs_click_group(package="scitex-sdk"))
        main.add_command(skills_click_group(package="scitex-sdk"))
    except ImportError:
        pass


_register_components()

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "PACKAGE", "gui", "main"]

# EOF
