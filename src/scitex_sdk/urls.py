"""Generic Django URL mounting with leaf-declared namespace compatibility.

``app_name`` remains Django's application namespace. A leaf may additionally
declare ``namespace_aliases = ("old_name",)`` in its URLconf. Each alias is an
instance namespace over the same relative URLconf, never a second view tree.
Hosts must use this helper to consume the declaration; plain Django include
does not support aliases. This is an unpublished coordinated SDK contract.
"""

from __future__ import annotations

import re
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.urls import URLResolver, include, path


class NamespaceCollision(ImproperlyConfigured):
    """A namespace already belongs to another mount in the same URL scope."""


def _existing_namespaces(patterns):
    names = set()
    for pattern in patterns:
        if not isinstance(pattern, URLResolver):
            continue
        if pattern.namespace:
            names.add(pattern.namespace)
            if pattern.app_name:
                # Django resolves application namespaces before instance
                # names. An alias must not be hidden by another application's
                # name even when that application uses a custom instance.
                names.add(pattern.app_name)
        else:
            # An unnamespaced include keeps its children's namespaces in the
            # current scope, even when it contributes a URL path prefix.
            names.update(_existing_namespaces(pattern.url_patterns))
    return names


def mount_urlpatterns(route, urlconf, *, namespace=None, existing=()):
    """Mount a URLconf and its declared aliases under one trusted prefix.

    ``urlconf`` is a module or dotted module name. ``namespace`` has Django's
    existing explicit-instance semantics. Pass all sibling patterns through
    ``existing`` to reject namespace ownership collisions before mounting.
    Route ownership remains the host's policy; aliases introduce no new URLs.
    """
    module = import_module(urlconf) if isinstance(urlconf, str) else urlconf
    primary = include(module, namespace=namespace)
    aliases = getattr(module, "namespace_aliases", ())
    if not isinstance(aliases, (list, tuple)):
        raise ImproperlyConfigured("namespace_aliases must be a list or tuple")
    if aliases and not primary[1]:
        raise ImproperlyConfigured("Namespace aliases require a Django app_name")
    names = list({name for name in (primary[1], primary[2]) if name})
    declared = set()
    additional = []
    for alias in aliases:
        if not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", alias):
            raise ImproperlyConfigured("Namespace aliases must be simple nonempty names")
        if alias == primary[1] or alias in declared:
            raise ImproperlyConfigured("Namespace aliases must be unique and distinct from app_name")
        declared.add(alias)
        if alias != primary[2]:
            names.append(alias)
            additional.append(alias)
    conflicts = set(names) & _existing_namespaces(existing)
    if conflicts:
        raise NamespaceCollision("URL namespace already mounted: " + ", ".join(sorted(conflicts)))
    return [path(route, primary)] + [
        path(route, include(module, namespace=alias)) for alias in additional
    ]


__all__ = ["NamespaceCollision", "mount_urlpatterns"]
