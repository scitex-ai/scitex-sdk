#!/usr/bin/env python3
"""Entry-point discovery of ``scitex.apis`` plugins, without importing them."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ._base import API_ENTRY_POINT_GROUP, ApiPluginContractError


@dataclass(frozen=True)
class ApiPluginRef:
    """One ``scitex.apis`` entry point, read WITHOUT importing it."""

    name: str
    target: str
    distribution: str = ""


def discover_api_plugins(entry_points: Iterable | None = None) -> list[ApiPluginRef]:
    """Every installed ``scitex.apis`` entry point, sorted by name.

    Mirrors :func:`scitex_sdk.app.plugins.discover_plugin_apps` deliberately: the
    value is kept as a STRING, so discovery never imports a leaf's code (a host
    reads this at settings time, and an import here would run every installed
    leaf inside the host's configuration phase).

    A duplicate NAME is REFUSED rather than resolved. Two distributions claiming
    one plugin name would make the loaded plugin a function of install order,
    and "the first one wins" ships the loser silently — exactly the failure a
    host cannot see and an operator cannot debug.
    """
    if entry_points is None:
        from importlib.metadata import entry_points as _entry_points

        entry_points = _entry_points(group=API_ENTRY_POINT_GROUP)
    found: dict[str, ApiPluginRef] = {}
    for ep in entry_points:
        if ep.name in found:
            raise ApiPluginContractError(
                f"two installed distributions publish the "
                f"{API_ENTRY_POINT_GROUP} entry point {ep.name!r} "
                f"({found[ep.name].target!r} from "
                f"{found[ep.name].distribution!r} and {ep.value!r}); whichever "
                "one a host loads would depend on install order, so give each "
                "plugin a distinct name"
            )
        dist = getattr(getattr(ep, "dist", None), "name", "") or ""
        found[ep.name] = ApiPluginRef(ep.name, ep.value, dist)
    return [found[key] for key in sorted(found)]

# EOF
