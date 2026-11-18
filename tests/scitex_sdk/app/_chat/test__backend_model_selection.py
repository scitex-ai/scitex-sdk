"""Model selection through actual providers and an owned Anthropic SSE endpoint.

No provider callable is replaced. One isolated child has dummy credentials,
blocks every connection except its own loopback server, and records the model
the real Anthropic client sends. LiteLLM construction makes no model request.
"""

import json
import os
import subprocess
import sys

import pytest

# name, preferred env, legacy env, explicit model, per-request override,
# expected default, expected wire model, expected warning text
CASES = [
    ("default", None, None, None, None, "claude-sonnet-4-20250514", "claude-sonnet-4-20250514", ""),
    ("preferred-bare", "preferred", None, None, None, "preferred", "preferred", ""),
    ("preferred-qualified", "anthropic/preferred", None, None, None, "preferred", "preferred", ""),
    ("legacy-bare", None, "legacy", None, None, "legacy", "legacy", "deprecated"),
    ("legacy-qualified", None, "anthropic/legacy", None, None, "legacy", "legacy", "deprecated"),
    ("conflict", "anthropic/preferred", "anthropic/legacy", None, None, "preferred", "preferred", "disagree"),
    ("same", "anthropic/same", "anthropic/same", None, None, "same", "same", ""),
    ("empty-preferred", "", "anthropic/legacy", None, None, "legacy", "legacy", "deprecated"),
    ("empty-both", "", "", None, None, "claude-sonnet-4-20250514", "claude-sonnet-4-20250514", ""),
    ("explicit", "anthropic/preferred", "anthropic/legacy", "explicit", None, "explicit", "explicit", ""),
    ("explicit-unchanged", "anthropic/preferred", None, "anthropic/explicit", None, "anthropic/explicit", "anthropic/explicit", ""),
    ("empty-explicit", "anthropic/preferred", None, "", None, "preferred", "preferred", ""),
    ("request-override", "anthropic/preferred", None, None, "request-model", "preferred", "request-model", ""),
]

PROBE = r'''
import io, json, logging, os, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

requests = []
class Endpoint(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append({'path': self.path, 'body': body})
        events = [
            {'type': 'message_start', 'message': {'id': 'msg_owned',
             'type': 'message', 'role': 'assistant', 'model': body['model'],
             'content': [], 'stop_reason': None, 'stop_sequence': None,
             'usage': {'input_tokens': 1, 'output_tokens': 0}}},
            {'type': 'content_block_start', 'index': 0,
             'content_block': {'type': 'text', 'text': ''}},
            {'type': 'content_block_delta', 'index': 0,
             'delta': {'type': 'text_delta', 'text': 'owned response'}},
            {'type': 'content_block_stop', 'index': 0},
            {'type': 'message_delta', 'delta': {'stop_reason': 'end_turn',
             'stop_sequence': None}, 'usage': {'output_tokens': 1}},
            {'type': 'message_stop'},
        ]
        payload = ''.join('event: '+e['type']+'\ndata: '+json.dumps(e)+'\n\n'
                          for e in events).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

server = ThreadingHTTPServer(('127.0.0.1', 0), Endpoint)
allowed = server.server_address
def refuse_external(event, args):
    if event == 'socket.connect' and args[1] != allowed:
        raise RuntimeError('model-selection control refuses external connections')
    if event == 'sqlite3.connect':
        raise RuntimeError('model-selection control refuses databases')
sys.addaudithook(refuse_external)
thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05})
thread.start()
os.environ['ANTHROPIC_BASE_URL'] = 'http://127.0.0.1:'+str(allowed[1])
os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
from scitex_sdk.app._chat._backends import get_chat_backend
output = {}
capture = io.StringIO()
handler = logging.StreamHandler(capture)
handler.setLevel(logging.WARNING)
logging.getLogger().addHandler(handler)
try:
    for name, preferred, legacy, explicit, request_model, *_ in json.loads(sys.argv[1]):
        for key in ('SCITEX_APP_LLM_MODEL', 'LLM_MODEL'):
            os.environ.pop(key, None)
        for key, value in [('SCITEX_APP_LLM_MODEL', preferred), ('LLM_MODEL', legacy)]:
            if value is not None:
                os.environ[key] = value
        os.environ['ANTHROPIC_API_KEY'] = 'owned-dummy-no-external-request'
        capture.seek(0)
        capture.truncate(0)
        backend = get_chat_backend(model=explicit)
        warnings = capture.getvalue()
        before = len(requests)
        events = list(backend.stream([{'role': 'user', 'content': 'owned prompt'}],
                                    model=request_model))
        assert len(requests) == before + 1, events
        output[name] = {'backend': type(backend).__name__,
                        'default': backend._default_model,
                        'request': requests[-1], 'events': events, 'warnings': warnings}
    os.environ.pop('ANTHROPIC_API_KEY')
    os.environ['SCITEX_APP_LLM_MODEL'] = 'openai/owned-model'
    os.environ.pop('LLM_MODEL', None)
    before = len(requests)
    for explicit in (None, 'explicit/provider-model'):
        backend = get_chat_backend(model=explicit)
        output['litellm-'+str(explicit)] = {
            'backend': type(backend).__name__, 'default': backend._default_model}
    assert len(requests) == before
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    assert not thread.is_alive()
print('MODEL_SELECTION='+json.dumps(output))
'''


@pytest.fixture(scope="module")
def selection(tmp_path_factory):
    owned = tmp_path_factory.mktemp("backend-model-selection")
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("ANTHROPIC_") or key.upper() in {
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        }:
            del environment[key]
    environment.update(SCITEX_DIR=str(owned / "scitex"), NO_PROXY="*")
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, json.dumps(CASES)],
        cwd=owned, env=environment, capture_output=True, text=True,
        check=True, timeout=30,
    )
    line = next(line for line in completed.stdout.splitlines()
                if line.startswith("MODEL_SELECTION="))
    observed = json.loads(line.partition("=")[2])
    (owned / "MODEL-SELECTION.json").write_text(json.dumps(observed, indent=2))
    return observed


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_anthropic_model_reaches_real_client(selection, case):
    name, _, _, _, _, default, wire_model, _warning = case
    observed = selection[name]
    assert (observed["backend"], observed["default"],
            observed["request"]["body"]["model"]) == (
                "AnthropicChatBackend", default, wire_model)


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_selection_preserves_stream_protocol_and_warnings(selection, case):
    observed = selection[case[0]]
    warning = case[-1]
    assert observed["request"]["path"] == "/v1/messages"
    assert observed["events"] == [
        {"type": "chunk", "text": "owned response"}, {"type": "done"}]
    if warning:
        assert warning in observed["warnings"]
    else:
        assert observed["warnings"] == ""


@pytest.mark.parametrize("explicit", [None, "explicit/provider-model"])
def test_litellm_selection_retains_provider_qualified_model(selection, explicit):
    assert selection["litellm-"+str(explicit)] == {
        "backend": "LiteLLMChatBackend", "default": explicit or "openai/owned-model"}
