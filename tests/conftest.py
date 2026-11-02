"""Shared component metadata fixture, valid for source and wheel runs."""
# Fence inherited store/libpq routing before importing pytest, Django or peers.
# CI also wraps phases before interpreter startup; this is the local collection floor.
import os
import importlib.util
from pathlib import Path

_store_spec = importlib.util.spec_from_file_location(
    "_sdk_test_store", Path(__file__).resolve().parents[1] / "scripts/ci-store-environment.py"
)
_store_guard = importlib.util.module_from_spec(_store_spec)
_store_spec.loader.exec_module(_store_guard)
_store_guard.protect_environment(os.environ)

import pytest
from tests._component_metadata import check_component_metadata

# The merged App/UI suite shares one Django process. Configure both owned
# components before module collection; inherited minimal per-file setup must
# not hide templates from the sibling component.
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="sdk-owned-tests",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF="scitex_sdk.creator.urls",
        INSTALLED_APPS=["django.contrib.staticfiles", "scitex_sdk.app", "scitex_sdk.ui", "scitex_sdk.creator"],
        TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}],
        DATABASES=({"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}} if os.environ.get("SCITEX_ACCESS_STRICT") == "1" else {}),
        STATIC_URL="/static/",
        LANGUAGE_CODE="en",
        USE_I18N=True,
    )
    django.setup()

@pytest.fixture
def check_metadata():
    return check_component_metadata
