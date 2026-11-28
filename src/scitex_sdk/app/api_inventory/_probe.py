#!/usr/bin/env python3
"""Live cross-check: GET every safe, parameter-free API path on a server.

Only ``GET`` is ever sent, never to a path that looks state-changing even on
GET (logout, verify, toggle, ...), never following redirects, and reading at
most a few KB of each body. A bearer token, when given, is read from an
environment variable and never echoed. Transient failures (a redeploying
server: connection refused, 502/503/504) are retried with backoff and every
attempt is timestamped.
"""

from __future__ import annotations

import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

#: Path words that make even a GET unsafe or meaningless to probe.
UNSAFE_WORDS = frozenset(
    {
        "logout",
        "signout",
        "delete",
        "remove",
        "toggle",
        "activate",
        "deactivate",
        "verify-email",
        "confirm",
        "unsubscribe",
        "cancel",
        "run",
        "execute",
        "submit",
        "start",
        "stop",
        "restart",
        "kill",
        "sync",
        "reset",
        "switch",
        "callback",
        "authorize",
        "webhook",
        "stream",
        "events",
        "impersonate",
        "purge",
        "rebuild",
        "install",
        "uninstall",
    }
)
RETRY_STATUSES = frozenset({502, 503, 504})
_PARAM = re.compile(r"[{}<>()*\[\]]")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe_safe(row: dict) -> bool:
    """Whether ``row`` may be probed with a GET."""
    path = row.get("path") or ""
    methods = set(row.get("methods") or ())
    if row.get("kind") not in ("rest", "asgi") or _PARAM.search(path):
        return False
    if not methods & {"GET", "ANY", "HEAD"}:
        return False
    words = set(re.split(r"[/_.-]", path.lower()))
    return not (words & UNSAFE_WORDS)


def classify(status: int | None, location: str) -> str:
    if status is None:
        return "unreachable"
    if 200 <= status < 300:
        return "open"
    if 300 <= status < 400:
        return (
            "login-redirect"
            if "login" in location or "signin" in location
            else "redirect"
        )
    return {
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        405: "method-not-allowed",
        429: "rate-limited",
    }.get(status, "client-error" if status < 500 else "server-error")


def _get(url: str, headers: dict, timeout: float) -> tuple:
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=timeout) as resp:
            resp.read(4096)
            return (
                resp.status,
                resp.headers.get("Content-Type", ""),
                resp.headers.get("Location", ""),
            )
    except urllib.error.HTTPError as err:
        err.read(4096)
        return (
            err.code,
            err.headers.get("Content-Type", ""),
            err.headers.get("Location", ""),
        )


def probe_one(
    base: str, path: str, *, headers: dict, timeout: float, retries: int
) -> dict:
    attempts = []
    status = ctype = None
    location = ""
    for attempt in range(retries + 1):
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            status, ctype, location = _get(base.rstrip("/") + path, headers, timeout)
            error = None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            status, error = None, type(exc).__name__
        attempts.append({"at": stamp, "status": status, "error": error})
        if status is not None and status not in RETRY_STATUSES:
            break
        time.sleep(min(2**attempt, 8))
    ctype = (ctype or "").split(";")[0].strip()
    location = location.split("?")[0]
    return {
        "status": status,
        "content_type": ctype,
        "location": location,
        "behaviour": classify(status, location),
        "error_problem_json": (ctype == "application/problem+json")
        if status is not None and status >= 400
        else None,
        "attempts": attempts,
    }


def probe_rows(
    rows: list[dict],
    base: str,
    *,
    host_header: str | None = None,
    token_env: str | None = None,
    timeout: float = 15.0,
    retries: int = 3,
    pause: float = 0.05,
) -> dict:
    """Probe every safe row in place (``row['live']``); return run metadata."""
    headers = {"User-Agent": "scitex-sdk-api-inventory", "Accept": "application/json"}
    if host_header:
        headers["Host"] = host_header
    token = os.environ.get(token_env) if token_env else None
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    probed = 0
    for row in rows:
        if not probe_safe(row):
            continue
        row["live"] = probe_one(
            base, row["path"], headers=headers, timeout=timeout, retries=retries
        )
        if token:
            auth = dict(headers, Authorization=f"Bearer {token}")
            with_token = probe_one(
                base, row["path"], headers=auth, timeout=timeout, retries=retries
            )
            row["live"]["with_token"] = {
                k: with_token[k] for k in ("status", "content_type", "behaviour")
            }
        probed += 1
        time.sleep(pause)
    return {
        "base": base,
        "host_header": host_header,
        "token_env": token_env if token else None,
        "started": started,
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "probed": probed,
    }


__all__ = ["UNSAFE_WORDS", "classify", "probe_one", "probe_rows", "probe_safe"]
