"""Actual IPv6 command parsing, loopback sockets, and owned runtime state."""

import json
import os
import socket
import subprocess
import sys
from urllib.parse import urlsplit

import pytest

from scitex_sdk.app import _gui_runtime, embed


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_runtime_status_url_round_trips_host_and_port(tmp_path, host):
    state = tmp_path / "gui.json"
    _gui_runtime.write_state(os.getpid(), 32101, host, str(tmp_path), state)
    before = state.read_bytes()
    result = _gui_runtime.status(state)
    parsed = urlsplit(result["url"])
    assert parsed.hostname == host
    assert parsed.port == 32101
    assert state.read_bytes() == before


@pytest.mark.parametrize("verb", ["serve", "open"])
def test_ipv6_cli_dry_run_prints_browser_usable_url(tmp_path, verb):
    config = tmp_path / "config.yaml"
    config.write_text("gui: {host: '::1'}\n")
    environment = dict(os.environ, SCITEX_SDK_CONFIG=str(config))
    environment.pop("SCITEX_SDK_GUI_PORT", None)
    result = subprocess.run(
        [sys.executable, "-m", "scitex_sdk", "gui", verb, "--dry-run"],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "http://[::1]:31301" in result.stdout


@pytest.mark.parametrize("hot_reload", [False, True])
@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_real_django_runserver_parses_bind_address_before_launch(
    tmp_path, host, hot_reload
):
    program = r"""
import json, sys
from django.conf import settings
from scitex_sdk.app._standalone import _allowed_hosts
settings.configure(SECRET_KEY="owned-ipv6-probe", DEBUG=False,
                   ALLOWED_HOSTS=_allowed_hosts(sys.argv[1]),
                   INSTALLED_APPS=["django.contrib.staticfiles"], DATABASES={})
import django
django.setup()
from django.test import RequestFactory
authority = "[::1]" if sys.argv[1] == "::1" else sys.argv[1]
assert RequestFactory().get("/", HTTP_HOST=f"{authority}:32101").get_host() == f"{authority}:32101"
from scitex_sdk.app._standalone import _run_server
class ObservedBeforeLaunch(Exception):
    pass
def observe(frame, event, argument):
    path = frame.f_code.co_filename.replace("\\", "/")
    if event == "call" and frame.f_code.co_name == "run" and path.endswith("/django/core/management/commands/runserver.py"):
        command = frame.f_locals["self"]
        options = frame.f_locals["options"]
        print(json.dumps(dict(address=command.addr, port=command.port,
                              ipv6=command.use_ipv6,
                              reload=options["use_reloader"],
                              insecure=options["insecure_serving"])))
        raise ObservedBeforeLaunch
sys.setprofile(observe)
try:
    _run_server(sys.argv[1], 32101, sys.argv[2] == "True")
except ObservedBeforeLaunch:
    pass
finally:
    sys.setprofile(None)
"""
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    result = subprocess.run(
        [sys.executable, "-c", program, host, str(hot_reload)],
        env=environment,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data == {
        "address": host,
        "port": "32101",
        "ipv6": host == "::1",
        "reload": hot_reload,
        "insecure": True,
    }


def test_ipv6_launcher_probes_actual_ipv6_socket_without_claiming_foreign_port(
    tmp_path,
):
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as listener:
        listener.bind(("::1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert embed._port_is_free("::1", port) is False
        state = tmp_path / "gui.json"

        def refuse_launch():
            raise AssertionError("Occupied IPv6 port must not launch a server")

        assert (
            embed.serve_gui(
                "owned-ipv6",
                str(tmp_path),
                port,
                "::1",
                False,
                refuse_launch,
                state_path=state,
            )
            == 1
        )
        assert not state.exists()
    assert embed._port_is_free("::1", port) is True


def test_ipv6_launcher_runs_and_clears_only_owned_state(tmp_path):
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as reservation:
        reservation.bind(("::1", 0))
        port = reservation.getsockname()[1]
    state = tmp_path / "gui.json"
    observations = []

    def run_server():
        observations.append(_gui_runtime.status(state))

    result = embed.serve_gui(
        "owned-ipv6", str(tmp_path), port, "::1", False, run_server, state_path=state
    )
    assert result == 0
    assert observations[0]["url"] == f"http://[::1]:{port}"
    assert not state.exists()
