#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Django registration for the shared chat models.

``ChatSession`` / ``ChatMessage`` declare ``app_label = "scitex_app"`` with
migrations under this module, so this config — name ``scitex_sdk.app._chat``,
label ``scitex_app`` — is the one installation that resolves both. It is the
successor to same-labelled legacy registrations carrying field-identical
history: same label, same tables, same dependency-free ``0001_initial``.

Install exactly one ``scitex_app``-labelled config per host. The legacy
companion and this config must never be installed together; Django fails
loud on the duplicate label rather than shadowing either side.
"""

from django.apps import AppConfig


class ScitexAppChatConfig(AppConfig):
    name = "scitex_sdk.app._chat"
    label = "scitex_app"
    verbose_name = "SciTeX Chat Sessions"
    default_auto_field = "django.db.models.BigAutoField"
