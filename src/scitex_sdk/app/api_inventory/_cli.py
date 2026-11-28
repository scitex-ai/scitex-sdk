#!/usr/bin/env python3
"""Click front ends: the shared ``<pkg> api list`` and ``scitex-sdk api inventory``.

A leaf gets its listing command with one line in its CLI::

    from scitex_sdk.app.api_inventory import api_click_group
    main.add_command(api_click_group(package="scitex-dataset"))

and ``scitex-dataset api list [--format json|csv|md]`` prints the package's
declared operations, its MCP tools and the rule findings — the same rows the
global aggregate is made of.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from ._aggregate import aggregate, discover_specs
from ._package import PackageSpec
from ._render import RENDERERS

FORMATS = click.Choice(sorted(RENDERERS))


def _emit(doc: dict, fmt: str, output: str | None) -> None:
    text = RENDERERS[fmt](doc)
    if output:
        Path(output).write_text(text, encoding="utf-8")
        click.echo(f"wrote {output}", err=True)
    else:
        click.echo(text, nl=False)


def _fail_on(doc: dict, strict: bool) -> None:
    if strict and doc["totals"]["programmatic"] != doc["totals"]["conformant"]:
        bad = doc["totals"]["programmatic"] - doc["totals"]["conformant"]
        raise click.ClickException(f"{bad} entries violate API rules (see --format md)")


def list_command(
    package: str, import_name: str | None = None, mcp_server: str | None = None
):
    """The ``list`` command for one package (operations + MCP tools + findings)."""

    @click.command("list")
    @click.option("--format", "fmt", type=FORMATS, default="md", show_default=True)
    @click.option(
        "--output", "-o", type=click.Path(dir_okay=False), help="Write to a file."
    )
    @click.option(
        "--strict", is_flag=True, help="Exit 1 when any entry violates a rule."
    )
    def _list(fmt: str, output: str | None, strict: bool) -> None:
        spec = PackageSpec(package, import_name=import_name, mcp_server=mcp_server)
        doc = aggregate([spec])
        _emit(doc, fmt, output)
        _fail_on(doc, strict)

    _list.help = (
        f"List {package}'s API operations and MCP tools with rule findings.\n\n"
        f"\b\nExample:\n  $ {package} api list\n  $ {package} api list --format json"
    )
    return _list


def api_click_group(
    package: str, import_name: str | None = None, mcp_server: str | None = None
):
    """A ``api`` click group with ``list`` bound to ``package``."""

    @click.group("api", invoke_without_command=True)
    @click.pass_context
    def api(ctx: click.Context) -> None:
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    api.help = f"Inspect the API surface of {package} (operations, MCP tools, rules)."
    api.add_command(list_command(package, import_name, mcp_server))
    return api


def load_env_file(path: str) -> int:
    """Set ``KEY=VALUE`` lines into the environment (values are never echoed)."""
    count = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        count += 1
    return count


@click.command("inventory")
@click.option(
    "--packages",
    default="auto",
    show_default=True,
    help="Comma-separated distributions, 'auto' (installed ecosystem) or 'none'.",
)
@click.option("--django-settings", help="DJANGO_SETTINGS_MODULE of a host to resolve.")
@click.option(
    "--django-root",
    type=click.Path(file_okay=False, exists=True),
    help="Host source root put on sys.path (e.g. a scitex-hub checkout).",
)
@click.option(
    "--env-file",
    type=click.Path(dir_okay=False, exists=True),
    help="KEY=VALUE file the host settings need (values never printed).",
)
@click.option(
    "--asgi", "asgi_module", help="ASGI module whose HTTP/websocket mounts to list."
)
@click.option(
    "--hosted-mcp", help="module:attr of the host's aggregating FastMCP server."
)
@click.option("--probe-base", help="Base URL to GET-probe safe public paths on.")
@click.option("--probe-host-header", help="Host header for the probe (origin tunnels).")
@click.option("--token-env", help="Env var holding a bearer token for a second probe.")
@click.option(
    "--no-pages", is_flag=True, help="Drop HTML page routes from the entries."
)
@click.option("--format", "fmt", type=FORMATS, default="md", show_default=True)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False),
    help="Write inventory.json, inventory.csv and index.md here.",
)
def inventory_command(
    packages,
    django_settings,
    django_root,
    env_file,
    asgi_module,
    hosted_mcp,
    probe_base,
    probe_host_header,
    token_env,
    no_pages,
    fmt,
    output_dir,
):
    """Inventory every API endpoint and MCP tool of the ecosystem (and a host).

    \b
    Example:
      $ scitex-sdk api inventory
      $ scitex-sdk api inventory --django-root ~/proj/scitex-hub \\
          --django-settings config.settings.settings_dev --asgi config.asgi \\
          --hosted-mcp scitex.mcp_server:mcp --output-dir out/
    """
    if env_file:
        load_env_file(env_file)
    if django_root:
        sys.path.insert(0, str(Path(django_root).resolve()))
    if django_settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = django_settings
        import django

        django.setup()
    if packages == "auto":
        specs = discover_specs()
    elif packages == "none":
        specs = []
    else:
        specs = [PackageSpec(p.strip()) for p in packages.split(",") if p.strip()]
    probe = None
    if probe_base:
        probe = {
            "base": probe_base,
            "host_header": probe_host_header,
            "token_env": token_env,
        }
    doc = aggregate(
        specs,
        urlconf=bool(django_settings),
        asgi_module=asgi_module,
        hosted_mcp=hosted_mcp,
        probe=probe,
        include_pages=not no_pages,
    )
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, kind in (
            ("inventory.json", "json"),
            ("inventory.csv", "csv"),
            ("index.md", "md"),
        ):
            (out / name).write_text(RENDERERS[kind](doc), encoding="utf-8")
        click.echo(f"wrote {out}/inventory.json, inventory.csv, index.md", err=True)
        return
    _emit(doc, fmt, None)


def sdk_api_group():
    """``scitex-sdk api``: the SDK's own ``list`` plus the global ``inventory``."""
    group = api_click_group("scitex-sdk")
    group.help = (
        "API surface: list scitex-sdk's own, or inventory the whole ecosystem/host."
    )
    group.add_command(inventory_command)
    return group


__all__ = [
    "api_click_group",
    "inventory_command",
    "list_command",
    "load_env_file",
    "sdk_api_group",
]
