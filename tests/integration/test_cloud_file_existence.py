"""Cloud file existence through the real HTTP client and an owned loopback server."""

from __future__ import annotations

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from scitex_sdk.app.sdk import _client
from scitex_sdk.app.sdk._cloud_files import CloudFilesBackend


class _OwnedFilesHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('/disconnect'):
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        status = int(self.path.rsplit('/', 1)[-1])
        payload = json.dumps({'content': 'owned-value'}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture(scope='module')
def owned_files_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _OwnedFilesHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


@pytest.fixture
def cloud_files(owned_files_server):
    keys = ['SCITEX_API_TOKEN', 'SCITEX_API_URL', 'NO_PROXY', 'no_proxy']
    previous = {key: os.environ.get(key) for key in keys}
    previous_client = _client._default_client
    os.environ.update(
        SCITEX_API_TOKEN='owned-inert-token',
        SCITEX_API_URL=owned_files_server,
        NO_PROXY='127.0.0.1',
        no_proxy='127.0.0.1',
    )
    _client.reset_client()
    try:
        yield CloudFilesBackend('owned-app')
    finally:
        _client._default_client = previous_client
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_existing_file_is_true(cloud_files):
    assert cloud_files.exists('200') is True


def test_missing_file_is_false(cloud_files):
    assert cloud_files.exists('404') is False


@pytest.mark.parametrize('status', [400, 401, 403, 408, 409, 429, 500, 503])
def test_other_http_errors_propagate(cloud_files, status):
    with pytest.raises(requests.HTTPError) as caught:
        cloud_files.exists(str(status))
    assert caught.value.response.status_code == status


def test_transport_error_propagates(cloud_files):
    with pytest.raises(requests.ConnectionError):
        cloud_files.exists('disconnect')
