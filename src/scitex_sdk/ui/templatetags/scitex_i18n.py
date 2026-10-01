#!/usr/bin/env python3
"""``{% scitex_js_catalog "<app package>" %}`` embeds that app's djangojs catalog."""

from __future__ import annotations

from django import template
from django.utils.html import json_script

from scitex_sdk.ui.i18n import js_catalog, js_catalog_element_id

register = template.Library()


@register.simple_tag
def scitex_js_catalog(*packages: str):
    """Render the active language's JS catalog as a json_script element."""
    return json_script(js_catalog(packages), js_catalog_element_id(packages))


# EOF
