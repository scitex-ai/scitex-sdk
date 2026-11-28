#!/usr/bin/env python3
"""``Deprecation`` / ``Sunset`` / ``Link`` headers on a host's legacy API routes.

API-H003 (docs/design/api-contract-v1/01-rules.md): a deprecated legacy route
answers exactly as before and additionally carries

* ``Deprecation: @<unix seconds>`` (RFC 9745, a structured-field Date),
* ``Sunset: <HTTP-date>`` (RFC 8594), and
* ``Link: <successor>; rel="successor-version"``, ``<doc>; rel="deprecation"``.

The host owns the list (it knows its legacy routes); this module owns the
header shapes, so every host spells them the same way. Configure::

    MIDDLEWARE += ["scitex_sdk.app.api_deprecation.LegacyApiDeprecationMiddleware"]
    SCITEX_API_BETA_LAUNCH_DATE = "2027-01-15"      # or None while undecided
    SCITEX_API_DEPRECATIONS = [
        {"pattern": r"^/api/project/list/$", "deprecated_at": "2026-11-28",
         "sunset_months_after_beta": 6, "successor": "/api/v1/hub/projects"},
    ]

``Sunset`` is the beta launch date plus ``sunset_months_after_beta``. While the
launch date is ``None`` no ``Sunset`` is sent: a guessed removal date would be
a promise nobody made. ``Deprecation`` and ``Link`` are sent regardless.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import format_datetime

DEFAULT_DOC = "https://scitex.ai/docs/api/deprecations"


def add_months(day: date, months: int) -> date:
    """``day`` plus ``months`` calendar months (clamped to the month's end)."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def _date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _midnight_utc(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Deprecation:
    """One deprecated legacy route family."""

    pattern: re.Pattern
    deprecated_at: date
    sunset_months_after_beta: int
    successor: str = ""
    doc: str = DEFAULT_DOC

    @classmethod
    def from_setting(cls, entry) -> Deprecation:
        months = int(entry.get("sunset_months_after_beta", 6))
        if months < 1:
            raise ValueError("sunset_months_after_beta must be >= 1")
        return cls(
            pattern=re.compile(entry["pattern"]),
            deprecated_at=_date(entry["deprecated_at"]),
            sunset_months_after_beta=months,
            successor=entry.get("successor", ""),
            doc=entry.get("doc", DEFAULT_DOC),
        )

    def headers(self, beta_launch: date | None) -> dict:
        out = {"Deprecation": f"@{int(_midnight_utc(self.deprecated_at).timestamp())}"}
        if beta_launch is not None:
            sunset = add_months(beta_launch, self.sunset_months_after_beta)
            out["Sunset"] = format_datetime(_midnight_utc(sunset), usegmt=True)
        links = [f'<{self.doc}>; rel="deprecation"']
        if self.successor:
            links.insert(0, f'<{self.successor}>; rel="successor-version"')
        out["Link"] = ", ".join(links)
        return out


def load(entries, beta_launch) -> tuple:
    """Validated ``(deprecations, beta_launch_date)`` from settings values."""
    return tuple(Deprecation.from_setting(e) for e in entries or ()), _date(beta_launch)


def headers_for(path: str, deprecations, beta_launch) -> dict:
    """The deprecation headers for ``path`` (empty when it is not deprecated)."""
    for item in deprecations:
        if item.pattern.search(path):
            return item.headers(beta_launch)
    return {}


class LegacyApiDeprecationMiddleware:
    """Adds API-H003 headers to responses of configured legacy routes."""

    def __init__(self, get_response):
        from django.conf import settings

        self.get_response = get_response
        self.deprecations, self.beta_launch = load(
            getattr(settings, "SCITEX_API_DEPRECATIONS", ()),
            getattr(settings, "SCITEX_API_BETA_LAUNCH_DATE", None),
        )

    def __call__(self, request):
        response = self.get_response(request)
        for key, value in headers_for(
            request.path, self.deprecations, self.beta_launch
        ).items():
            if key == "Link" and response.has_header("Link"):
                value = f"{response['Link']}, {value}"
            response[key] = value
        return response


__all__ = [
    "Deprecation",
    "LegacyApiDeprecationMiddleware",
    "add_months",
    "headers_for",
    "load",
]
