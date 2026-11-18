"""Real installed/source creator CLI lifecycle, confined to owned state and sockets."""

import http.cookiejar
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import scitex_sdk
from scitex_sdk.app._gui_runtime import state_path_env_var
from scitex_sdk.cli import PACKAGE

# Executed at interpreter startup, before the real CLI. These are effect guards,
# not replacements for the server, state resolver, HTTP stack, or signal handlers.
GUARD = r"""
import os, sys
port = int(os.environ['SDK_TEST_PORT'])
owned_pid = int(os.environ.get('SDK_TEST_PID', str(os.getpid())))
def guard(event, args):
    if event in {'socket.connect', 'subprocess.Popen', 'os.system', 'sqlite3.connect'}:
        raise RuntimeError('CLI lifecycle fixture refuses outbound/process/store effects')
    if event == 'socket.bind' and args[1] != ('127.0.0.1', port):
        raise RuntimeError('CLI lifecycle fixture binds only its owned loopback port')
    if event == 'os.kill' and (args[0] != owned_pid or args[1] not in (0, 15)):
        raise RuntimeError('CLI lifecycle fixture signals only its owned child')
sys.addaudithook(guard)
import scitex_sdk
sys.stderr.write("SDK_LIFECYCLE_ORIGIN=" + str(scitex_sdk.__file__) + "\n")
"""


def test_real_creator_cli_serves_and_stops_only_its_owned_instance(tmp_path):
    guard_dir = tmp_path / "guard"
    guard_dir.mkdir()
    (guard_dir / "sitecustomize.py").write_text(GUARD)
    state = tmp_path / "gui.json"
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "gui.yaml"
    config.write_text("gui: {}\n")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = dict(os.environ)
    env.pop("DJANGO_SETTINGS_MODULE", None)
    env.update(
        HOME=str(home), SCITEX_DIR=str(home / ".scitex"),
        SCITEX_WORKING_DIR=str(tmp_path), SCITEX_SDK_CONFIG=str(config),
        SCITEX_LANGUAGE_CODE="en", SDK_TEST_PORT=str(port),
        PYTHONPATH=os.pathsep.join([
            str(guard_dir),
            *[str(Path(value).resolve()) for value in env.get("PYTHONPATH", "").split(os.pathsep) if value],
        ]),
    )
    env[state_path_env_var(PACKAGE)] = str(state)
    command = [sys.executable, "-m", "scitex_sdk", "gui"]

    def cli(*args):
        return subprocess.run(
            [*command, *args], cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=20, check=False,
        )

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    base = f"http://127.0.0.1:{port}"
    with (tmp_path / "server.log").open("wb") as log:
        child = subprocess.Popen(
            [*command, "serve", "--host", "127.0.0.1", "--port", str(port)],
            cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        env["SDK_TEST_PID"] = str(child.pid)
        try:
            deadline = time.monotonic() + 10
            while True:
                assert child.poll() is None, (tmp_path / "server.log").read_text()
                try:
                    response = opener.open(base + "/", timeout=1)
                    break
                except urllib.error.URLError:
                    assert time.monotonic() < deadline, "Owned CLI startup exceeded 10s"
                    time.sleep(0.1)
            assert "SDK_LIFECYCLE_ORIGIN=" + str(scitex_sdk.__file__) in (
                tmp_path / "server.log"
            ).read_text()
            html = response.read().decode()
            assert response.status == 200 and html.count("ws-pane-unused") == 3
            token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)[1]
            assert json.loads(state.read_text())["pid"] == child.pid
            status = cli("status", "--json")
            assert status.returncode == 0, status.stderr
            observed = json.loads(status.stdout)
            assert observed["running"] and observed["pid"] == child.pid
            assert observed["url"] == base and observed["project"] == str(tmp_path)
            payload = json.dumps({"label": "Owned CLI Probe", "starter": "blank"}).encode()
            request = urllib.request.Request(
                base + "/api/validate-input", data=payload,
                headers={"Content-Type": "application/json"},
            )
            try:
                opener.open(request, timeout=2)
            except urllib.error.HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError("Tokenless real CLI request was accepted")
            request.add_header("X-CSRFToken", token)
            with opener.open(request, timeout=2) as validated:
                assert validated.status == 200 and json.load(validated)["ok"]
            duplicate = cli("serve", "--host", "127.0.0.1", "--port", str(port))
            assert duplicate.returncode == 1 and "already running" in duplicate.stderr
            before = state.read_bytes()
            assert cli("stop").returncode == 1
            dry_run = cli("stop", "--dry-run", "--json")
            assert dry_run.returncode == 0 and json.loads(dry_run.stdout)["would_stop"]
            assert state.read_bytes() == before and child.poll() is None
            stopped = cli("stop", "--yes", "--json")
            assert stopped.returncode == 0, stopped.stderr
            assert json.loads(stopped.stdout) == {
                "stopped": True, "pid": child.pid, "terminated": True,
            }
            child.wait(timeout=5)
            assert not state.exists()
            final = cli("status", "--json")
            assert final.returncode == 0 and json.loads(final.stdout) == {"running": False}
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
