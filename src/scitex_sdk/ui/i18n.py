#!/usr/bin/env python3
"""Client-side translations for SciTeX apps, built from Django's djangojs catalogs.

A leaf app keeps its JS/TS messages in ``<django app path>/locale/<lang>/
LC_MESSAGES/djangojs.po``. The page embeds the active language's catalog with::

    {% load scitex_i18n %}
    {% scitex_js_catalog "figrecipe._django" %}

and the TypeScript side reads it with ``gettext`` / ``ngettext`` / ``interpolate``
from ``ts/_base/gettext.ts``. The same tag serves standalone and mounted pages,
because the language comes from Django's active language in both.
"""

from __future__ import annotations

from typing import Iterable, Optional, Union

__all__ = [
    "JS_CATALOG_DOMAIN",
    "JS_CATALOG_ELEMENT_PREFIX",
    "js_catalog",
    "js_catalog_element_id",
]

JS_CATALOG_DOMAIN = "djangojs"

#: The TS reader collects every ``<script type="application/json">`` whose id starts with this.
JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-"


def _as_package_list(packages: Union[str, Iterable[str]]) -> list[str]:
    if isinstance(packages, str):
        return [packages]
    return list(packages)


def js_catalog(
    packages: Union[str, Iterable[str]], language: Optional[str] = None
) -> dict:
    """Return ``{"language", "plural", "catalog"}`` for the given installed app packages.

    ``packages`` are app config names (``"figrecipe._django"``), exactly as
    Django's ``JavaScriptCatalog`` takes them. ``language`` defaults to the
    active language.
    """
    from django.utils.translation import get_language
    from django.utils.translation.trans_real import DjangoTranslation
    from django.views.i18n import JavaScriptCatalog

    package_list = _as_package_list(packages)
    resolved_language = language or get_language() or "en"
    catalog_view = JavaScriptCatalog(domain=JS_CATALOG_DOMAIN, packages=package_list)
    catalog_view.translation = DjangoTranslation(
        resolved_language,
        domain=JS_CATALOG_DOMAIN,
        localedirs=catalog_view.get_paths(package_list),
    )
    return {
        "language": resolved_language,
        "plural": catalog_view.get_plural(),
        "catalog": catalog_view.get_catalog(),
    }


def js_catalog_element_id(packages: Union[str, Iterable[str]]) -> str:
    """The json_script element id for these packages, unique per app on a page."""
    joined = "-".join(_as_package_list(packages))
    return JS_CATALOG_ELEMENT_PREFIX + joined.replace(".", "-").replace("_", "-")


# EOF
