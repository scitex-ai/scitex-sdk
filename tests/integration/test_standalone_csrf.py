"""Actual standalone settings must protect unsafe GUI requests with CSRF."""

import json
import os
import subprocess
import sys

import pytest

PROGRAM = r"""
import json, re, sys
from django.conf import settings
host = sys.argv[1] == "host"
if host:
    settings.configure(
        SECRET_KEY="owned-host-csrf", DEBUG=False, ALLOWED_HOSTS=["127.0.0.1"],
        ROOT_URLCONF="scitex_sdk.creator.urls", DATABASES={}, STATIC_URL="/static/",
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.app", "scitex_sdk.ui", "scitex_sdk.creator"],
        TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates", "APP_DIRS":True}],
        MIDDLEWARE=["django.middleware.csrf.CsrfViewMiddleware"],
        SCITEX_APP_MODE="host-owned-csrf-contract",
    )
    before = list(settings.MIDDLEWARE)
def refuse(event, args):
    if event in {"socket.connect", "socket.bind", "sqlite3.connect", "subprocess.Popen", "os.kill"}:
        raise RuntimeError("CSRF control refuses external/database/process effects")
sys.addaudithook(refuse)
from scitex_sdk.app._standalone import _configure_django
_configure_django("scitex_sdk.creator")
host_preserved = not host or (settings.MIDDLEWARE==before and settings.SCITEX_APP_MODE=="host-owned-csrf-contract")
import django
django.setup()
from django.test import Client
client = Client(enforce_csrf_checks=True, HTTP_HOST="127.0.0.1")
page = client.get("/")
token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode())[1]
payload = {"label":"Owned CSRF Probe", "description":"Record samples", "starter":"blank"}
missing = client.post("/api/validate-input", payload, content_type="application/json")
valid = client.post("/api/validate-input", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token)
print(json.dumps({"page_status":page.status_code, "missing_status":missing.status_code,
                  "valid_status":valid.status_code, "valid_body":valid.json(),
                  "CSRF_enabled":"django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE,
                  "host_settings_preserved":host_preserved}))
"""


@pytest.mark.parametrize("mode", ["standalone", "host"])
def test_actual_settings_require_token_and_preserve_configured_host(tmp_path, mode):
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    environment["SCITEX_DIR"] = str(tmp_path / "owned-state")
    result = subprocess.run(
        [sys.executable, "-c", PROGRAM, mode],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "page_status": 200,
        "missing_status": 403,
        "valid_status": 200,
        "valid_body": {"ok": True, "errors": []},
        "CSRF_enabled": True,
        "host_settings_preserved": True,
    }
