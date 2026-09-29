#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django AppConfig for the SciTeX App Creator wizard.

Subclasses ``scitex_app._django.ScitexAppConfig`` while the app
contract still lives in scitex-app (facade step: implementation moves
here gradually), falling back to Django's plain ``AppConfig``
otherwise — the same idiom the leaves use. A host that vendors this
package without the engine installed still boots.

``label`` is the fully-namespaced ``scitex_sdk_creator`` rather than a
short generic name like ``creator`` — scitex-hub hit a real collision
bug where two apps falling back to the same generic label raised
``ImproperlyConfigured`` at hub boot. ``default = True`` is the other
half of that fix.
"""

from __future__ import annotations

try:
    from scitex_app._django import ScitexAppConfig
except ImportError:  # engine not installed — standalone still boots
    from django.apps import AppConfig as ScitexAppConfig  # type: ignore[no-redef]


class AppCreatorConfig(ScitexAppConfig):  # type: ignore[misc]
    """AppConfig for the SDK-served app-creator wizard."""

    default = True
    name = "scitex_sdk.creator"
    label = "scitex_sdk_creator"
    verbose_name = "SciTeX App Creator"


__all__ = ["AppCreatorConfig"]

# EOF
