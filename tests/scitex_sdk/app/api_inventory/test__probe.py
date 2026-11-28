"""The live GET probe against a real local HTTP server."""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from scitex_sdk.app.api_inventory._probe import probe_rows, probe_safe

TOKEN_ENV = "SCITEX_SDK_INVENTORY_TEST_TOKEN"
SEEN = []


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        SEEN.append((self.command, self.path, self.headers.get("Authorization")))
        if self.path == "/api/v1/notes/notes":
            self.send_response(401)
            self.send_header("Content-Type", "application/problem+json")
        elif self.path == "/api/legacy/":
            self.send_response(302)
            self.send_header("Location", "/auth/login/?next=/api/legacy/")
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def token():
    os.environ[TOKEN_ENV] = "t-123"
    yield "t-123"
    os.environ.pop(TOKEN_ENV, None)


@pytest.fixture(scope="module")
def probed(token):
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    SEEN.clear()
    rows = [
        _row("/api/v1/notes/notes"),
        _row("/api/legacy/"),
        _row("/api/ok"),
        _row("/api/x", methods=("POST",)),
    ]
    meta = probe_rows(
        rows, f"http://127.0.0.1:{httpd.server_port}", token_env=TOKEN_ENV, pause=0
    )
    httpd.shutdown()
    return rows, meta


def _row(path, methods=("GET",), kind="rest"):
    return {"path": path, "methods": list(methods), "kind": kind}


@pytest.mark.parametrize(
    "row",
    [
        _row("/api/auth/logout/"),
        _row("/api/items/{item_id}"),
        _row("/api/items", methods=("POST",)),
        _row("/", kind="page"),
    ],
)
def test_unsafe_parameterized_or_non_get_paths_are_never_probed(row):
    # Arrange
    candidate = row
    # Act
    safe = probe_safe(candidate)
    # Assert
    assert safe is False


def test_an_unrestricted_api_path_is_probed():
    # Arrange
    row = _row("/api/status/", methods=("ANY",))
    # Act
    safe = probe_safe(row)
    # Assert
    assert safe is True


def test_a_401_problem_response_is_recorded(probed):
    # Arrange
    rows, _ = probed
    # Act
    live = rows[0]["live"]
    # Assert
    assert (live["behaviour"], live["error_problem_json"]) == ("unauthorized", True)


def test_a_login_redirect_is_recorded_without_following_it(probed):
    # Arrange
    rows, _ = probed
    # Act
    live = rows[1]["live"]
    # Assert
    assert (live["behaviour"], live["location"]) == ("login-redirect", "/auth/login/")


def test_a_post_only_row_is_not_probed(probed):
    # Arrange
    rows, meta = probed
    # Act
    counted = (meta["probed"], "live" in rows[3])
    # Assert
    assert counted == (3, False)


def test_only_get_is_ever_sent(probed):
    # Arrange
    _ = probed
    # Act
    methods = {method for method, _, _ in SEEN}
    # Assert
    assert methods == {"GET"}


def test_the_token_is_sent_but_never_recorded(probed, token):
    # Arrange
    rows, meta = probed
    # Act
    sent = ("GET", "/api/ok", f"Bearer {token}") in SEEN
    # Assert
    assert (sent, token in repr(rows) + repr(meta)) == (True, False)
