#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL patterns for the SciTeX SDK (app-maker) wizard.

The standalone server (``scitex-sdk gui serve``) serves this module at the
root via ``ROOT_URLCONF = "scitex_sdk.creator.urls"``. Hosts mount the
same module under their own prefix — scitex-hub mounts it at ``apps/new/``
(login-wrapped); ``apps/sdk/`` is the prepared canonical app home for
consistency with the other ``/apps/<slug>/`` leaves.

Namespaced via ``app_name`` so a host's ``{% url %}`` lookups never
collide with another app's route names. Client fetch URLs are RELATIVE
(``api/create``), so both layouts work with no mount-prefix plumbing.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "scitex_sdk_creator"

urlpatterns = [
    path("", views.index, name="index"),
    path("healthz", views.healthz, name="healthz"),
    path("api/starters", views.api_starters, name="api_starters"),
    path("api/validate-input", views.api_validate_input, name="api_validate_input"),
    path("api/create", views.api_create, name="api_create"),
    path("api/validate-app", views.api_validate_app, name="api_validate_app"),
    path("api/publish", views.api_publish, name="api_publish"),
    path("api/dev-install", views.api_dev_install, name="api_dev_install"),
]

# EOF
