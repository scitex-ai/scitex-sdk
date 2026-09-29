#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standalone server adapter for the SciTeX App Creator wizard.

Boots the SAME Django app a host mounts (``scitex_sdk.creator``). The
serving machinery (guarded launcher, runtime state, workspace shell)
comes from the engine package — ``scitex_app.embed`` — until the
implementation consolidates into the SDK.

Top-level imports are stdlib-only so ``scitex-sdk gui --help`` never
needs Django; the web stack is imported lazily, inside the functions
that serve.
"""

from __future__ import annotations

from functools import partial
from typing import Callable

#: This wizard's fixed slot: the first 3130X overflow port. 3129X is
#: full per scitex-dev's reserved-port scheme (storage 31290 through
#: cards 31299, live-paper 31300), so a server that silently drifted to
#: a different port would be lying about where it is.
DEFAULT_PORT = 31301
DEFAULT_HOST = "127.0.0.1"

APP_MODULE = "scitex_sdk.creator"


def _run_server(
    *,
    port: int = DEFAULT_PORT,
    host: str = "127.0.0.1",
    open_browser: bool = False,
    hot_reload: bool = False,
) -> None:
    from scitex_app.embed import run_standalone

    run_standalone(
        app_module=APP_MODULE,
        port=port,
        host=host,
        open_browser=open_browser,
        hot_reload=hot_reload,
    )


def run(
    *,
    port: int = DEFAULT_PORT,
    host: str = "127.0.0.1",
    open_browser: bool = False,
    hot_reload: bool = False,
) -> None:
    """Run the wizard in the foreground. ``run_server`` for ``serve_gui``."""
    _run_server(
        port=port, host=host, open_browser=open_browser, hot_reload=hot_reload
    )


def run_server(
    *,
    port: int = DEFAULT_PORT,
    host: str = "127.0.0.1",
    hot_reload: bool = False,
) -> Callable[[], None]:
    """A zero-arg blocking callable for the guarded launcher."""
    return partial(
        _run_server, port=port, host=host, open_browser=False, hot_reload=hot_reload
    )


def serve(
    *,
    package: str,
    project_dir: str,
    port: int,
    host: str,
    force: bool = False,
    hot_reload: bool = False,
) -> int:
    """Launch the guarded standalone server. Returns an exit code."""
    from scitex_app.embed import serve_gui

    return serve_gui(
        package=package,
        project_dir=project_dir,
        port=port,
        host=host,
        force=force,
        run_server=run_server(port=port, host=host, hot_reload=hot_reload),
    )


__all__ = [
    "APP_MODULE",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "run",
    "run_server",
    "serve",
]

# EOF
