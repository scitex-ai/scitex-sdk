#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django AppConfig for the SciTeX App Creator wizard.

Uses the SDK-owned leaf AppConfig contract.

``label`` is the fully-namespaced ``scitex_sdk_creator`` rather than a
short generic name like ``creator`` — scitex-hub hit a real collision
bug where two apps falling back to the same generic label raised
``ImproperlyConfigured`` at hub boot. ``default = True`` is the other
half of that fix.
"""

from __future__ import annotations

from scitex_sdk.app._django import ScitexAppConfig

class AppCreatorConfig(ScitexAppConfig):  # type: ignore[misc]
    """AppConfig for the SDK-served app-creator wizard."""

    default = True
    name = "scitex_sdk.creator"
    label = "scitex_sdk_creator"
    verbose_name = "SciTeX App Creator"


__all__ = ["AppCreatorConfig"]

# EOF
