#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django model autodiscovery for the shared chat app.

The model classes live in :mod:`_models` (kept import-light so Belonging
checks and migrations never pull in streaming backends); this module only
re-exports them so Django's ``<app>.models`` autodiscovery registers them
under the installed ``scitex_app`` label.
"""

from ._models import ChatMessage, ChatSession

__all__ = ["ChatMessage", "ChatSession"]
