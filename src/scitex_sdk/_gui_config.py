"""SDK GUI host/port configuration; process-control flags stay CLI-only."""

from __future__ import annotations

import os
from pathlib import Path

import click
from scitex_config import PriorityConfig, load_yaml
from scitex_config._ecosystem import local_state


def resolve_gui_options(ctx: click.Context, *, host: str, port: int) -> tuple[str, int]:
    """Resolve CLI > selected YAML > GUI environment > command defaults.

    Selection and parsing reuse the owning configuration package. Read only
    host/port; a file cannot enable remote binding or process-control flags.
    """
    explicit_path = (ctx.obj or {}).get("sdk_gui_config_path")
    environment_path = os.environ.get("SCITEX_SDK_CONFIG")
    selected = explicit_path if explicit_path is not None else environment_path
    required = selected is not None and (explicit_path is not None or bool(selected))
    if required and not selected:
        raise click.ClickException("SDK GUI configuration path must not be empty.")
    path = (
        Path(selected).expanduser()
        if required
        else local_state.path("sdk", "config.yaml")
    )
    try:
        if not path.exists() and not path.is_symlink() and not required:
            data = {}
        else:
            data = load_yaml(path)
    except (OSError, ValueError, ImportError) as exc:
        raise click.ClickException(
            f"Cannot read SDK GUI configuration: {path}. "
            "Check the selected file and YAML syntax."
        ) from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise click.ClickException("SDK GUI configuration must be a YAML mapping.")
    gui = data.get("gui", {})
    if not isinstance(gui, dict):
        raise click.ClickException("SDK GUI configuration 'gui' must be a mapping.")
    if gui.keys() - {"host", "port"}:
        raise click.ClickException("SDK GUI configuration supports only host and port.")
    if "host" in gui and (not isinstance(gui["host"], str) or not gui["host"]):
        raise click.ClickException(
            "SDK GUI configuration host must be a nonempty string."
        )
    if "port" in gui and type(gui["port"]) is not int:
        raise click.ClickException("SDK GUI configuration port must be a YAML integer.")

    resolver = PriorityConfig(config_dict=gui, env_prefix="SCITEX_SDK_GUI_")
    command_line = click.core.ParameterSource.COMMANDLINE
    try:
        effective_host = resolver.resolve(
            "host",
            direct_val=host
            if ctx.get_parameter_source("host") == command_line
            else None,
            default=host,
        )
        effective_port = resolver.resolve(
            "port",
            direct_val=port
            if ctx.get_parameter_source("port") == command_line
            else None,
            default=port,
            type=int,
        )
    except (TypeError, ValueError) as exc:
        raise click.ClickException(
            "SDK GUI host/port environment values are invalid."
        ) from exc
    if (
        not isinstance(effective_host, str)
        or not effective_host
        or effective_host != effective_host.strip()
    ):
        raise click.ClickException(
            "SDK GUI host must be a nonempty hostname without surrounding whitespace."
        )
    if type(effective_port) is not int or not 1 <= effective_port <= 65535:
        raise click.ClickException("SDK GUI port must be an integer from 1 to 65535.")
    return effective_host, effective_port
