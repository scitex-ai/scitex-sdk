#!/usr/bin/env python3
"""What a Django view accepts: HTTP methods, credential modes, permission, CSRF.

Detection reads the real callables first — wrapper closures
(``require_http_methods`` keeps ``request_method_list``, ``user_passes_test``
keeps ``test_func``), DRF ``authentication_classes``/``permission_classes``,
class MROs, ``csrf_exempt`` attributes — and only then the view's source
(decorator names, inline ``request.user`` checks, custom key headers).
``auth_evidence`` records what each verdict was based on, so a reader can
audit a row instead of trusting it.
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
from functools import cache, lru_cache

_HTTP = ("get", "post", "put", "patch", "delete")
_DRF_AUTH = {
    "session": "session",
    "jwt": "jwt",
    "apikey": "api-key",
    "api_key": "api-key",
    "oauth": "oauth",
    "token": "token",
    "basic": "basic",
}
_GATE_DECORATORS = ("login_required", "staff_member_required", "superuser_required")


def chain(fn) -> list:
    """The wrapper chain of a view: outermost first, then each ``__wrapped__``."""
    seen = []
    while fn is not None and fn not in seen:
        seen.append(fn)
        fn = getattr(fn, "__wrapped__", None)
    return seen


def closure(fn) -> dict:
    code = getattr(fn, "__code__", None)
    cells = getattr(fn, "__closure__", None) or ()
    if code is None:
        return {}
    out = {}
    for name, cell in zip(code.co_freevars, cells):
        try:
            out[name] = cell.cell_contents
        except ValueError:
            continue
    return out


@cache
def source(obj) -> str:
    try:
        return textwrap.dedent(inspect.getsource(obj))
    except (OSError, TypeError):
        return ""


def decorator_names(obj) -> list[str]:
    src = source(obj)
    try:
        tree = ast.parse(src) if src else None
    except SyntaxError:
        tree = None
    node = tree.body[0] if tree is not None and tree.body else None
    names = []
    for dec in getattr(node, "decorator_list", ()):
        target = dec.func if isinstance(dec, ast.Call) else dec
        names.append(ast.unparse(target).split(".")[-1])
        if isinstance(dec, ast.Call) and names[-1] == "method_decorator" and dec.args:
            names.append(ast.unparse(dec.args[0]).split(".")[-1].split("(")[0])
    return names


def view_target(callback):
    """``(kind, obj)`` — the class or innermost function that implements it."""
    cls = getattr(callback, "view_class", None) or getattr(callback, "cls", None)
    if cls is not None:
        return "class", cls
    return "function", inspect.unwrap(callback)


def is_drf(callback) -> bool:
    kind, target = view_target(callback)
    return kind == "class" and hasattr(target, "authentication_classes")


def _methods_from_source(src: str) -> set[str]:
    found = set(re.findall(r"request\.method\s*(?:==|!=)\s*['\"]([A-Z]+)['\"]", src))
    for group in re.findall(
        r"request\.method\s+(?:not\s+)?in\s*[\(\[\{]([^\)\]\}]*)", src
    ):
        found |= set(re.findall(r"['\"]([A-Z]+)['\"]", group))
    return found


def http_methods(callback) -> list[str]:
    """The methods a view answers; ``ANY`` when nothing restricts them."""
    actions = getattr(callback, "actions", None)
    if actions:
        return sorted({m.upper() for m in actions})
    kind, target = view_target(callback)
    if kind == "class":
        allowed = getattr(target, "http_method_names", _HTTP)
        found = [m.upper() for m in _HTTP if m in allowed and hasattr(target, m)]
        return found or ["ANY"]
    for fn in chain(callback):
        methods = closure(fn).get("request_method_list")
        if methods:
            return sorted(m.upper() for m in methods)
    names = set(decorator_names(target))
    for dec, method in (
        ("require_GET", ["GET"]),
        ("require_POST", ["POST"]),
        ("require_safe", ["GET", "HEAD"]),
    ):
        if dec in names:
            return method
    found = _methods_from_source(source(target))
    return sorted(found) if found else ["ANY"]


def _test_func_kind(fn) -> str | None:
    names = set(getattr(getattr(fn, "__code__", None), "co_names", ()) or ())
    for attr, verdict in (
        ("is_superuser", "superuser"),
        ("is_staff", "staff"),
        ("has_perms", "permission"),
        ("has_perm", "permission"),
        ("is_authenticated", "login"),
    ):
        if attr in names:
            return verdict
    return None


def classify_name(name: str) -> set[str]:
    """Credential modes a decorator/mixin/class name announces."""
    low = name.lower()
    modes = set()
    if "api_key" in low or "apikey" in low:
        modes.add("api-key")
    if "jwt" in low:
        modes.add("jwt")
    if "oauth" in low:
        modes.add("oauth")
    if "signature" in low or "hmac" in low or "webhook_secret" in low:
        modes.add("signature")
    return modes


def _wrapper_modes(fn) -> tuple:
    """A decorator layer's real name (``functools.wraps`` hides it) and modes.

    ``co_qualname`` survives ``wraps``; the names the wrapper's own code
    calls (``reject_unsigned_gitea_webhook``) say what it checks.
    """
    code = getattr(fn, "__code__", None)
    if code is None:
        return "", set()
    qual = getattr(code, "co_qualname", code.co_name)
    deco = qual.split(".<locals>.")[0] if ".<locals>." in qual else qual
    found = classify_name(deco)
    for name in code.co_names:
        found |= classify_name(name)
    return deco, found


def _drf_profile(target, callback) -> tuple:
    modes, perms, evidence = set(), [], []
    auth_classes = target.authentication_classes
    for cls in auth_classes:
        low = cls.__name__.lower()
        evidence.append(f"drf-auth:{cls.__name__}")
        modes |= {mode for key, mode in _DRF_AUTH.items() if key in low} or {"custom"}
    for cls in getattr(target, "permission_classes", ()):
        perms.append(cls.__name__)
        evidence.append(f"drf-perm:{cls.__name__}")
    gated = any(p != "AllowAny" for p in perms)
    # DRF enforces CSRF itself for session-authenticated requests.
    names = {c.__name__ for c in auth_classes}
    csrf = "SessionAuthentication" not in names and bool(
        getattr(callback, "csrf_exempt", False)
    )
    return modes, perms, evidence, gated, csrf


def _django_profile(kind, target, callback, middleware_bearer) -> tuple:
    modes, perms, evidence = set(), [], []
    gated = False
    csrf = bool(getattr(callback, "csrf_exempt", False))
    layers = chain(callback)
    if kind == "class":
        layers += chain(getattr(target, "dispatch", None))
        for base in inspect.getmro(target):
            bname = base.__name__
            if bname in ("LoginRequiredMixin",):
                gated = True
                evidence.append(f"mixin:{bname}")
            elif bname in ("UserPassesTestMixin", "PermissionRequiredMixin"):
                gated = True
                perms.append(bname)
                evidence.append(f"mixin:{bname}")
            modes |= classify_name(bname)
    for fn in layers:
        test = closure(fn).get("test_func")
        if test is not None:
            verdict = _test_func_kind(test) or "test"
            gated = True
            evidence.append(f"user_passes_test:{verdict}")
            if verdict != "login":
                perms.append(verdict)
        if fn is not inspect.unwrap(callback):
            deco, found = _wrapper_modes(fn)
            if found:
                evidence.append(f"decorator:{deco}")
                modes |= found
                gated = True
    for name in decorator_names(target):
        found = classify_name(name)
        if found:
            modes |= found
            gated = True
            evidence.append(f"decorator:{name}")
        elif name in _GATE_DECORATORS:
            gated = True
            evidence.append(f"decorator:{name}")
            if name != "login_required":
                perms.append(name.replace("_member", "").replace("_required", ""))
        elif name == "csrf_exempt":
            csrf = True
    src = source(target)
    if not gated and re.search(
        r"request\.user\.is_(authenticated|superuser|staff)", src
    ):
        gated = True
        evidence.append("inline:request.user check")
        perms += [lvl for lvl in ("superuser", "staff") if f"is_{lvl}" in src]
    if re.search(r"X-SCITEX-API-KEY|HTTP_X_SCITEX_API_KEY|['\"]api_key['\"]", src):
        modes.add("custom-key-header")
        evidence.append("inline:custom api-key header/param")
    if re.search(r"HTTP_AUTHORIZATION|headers\.get\(['\"]Authorization", src) and re.search(
        r"api_key|APIKey", src
    ):
        modes.add("api-key")
        gated = True
        evidence.append("inline:Authorization bearer resolves an API key")
    if re.search(
        r"X-Gitea-Signature|Stripe-Signature|HTTP_[A-Z_]*SIGNATURE|construct_event|"
        r"compare_digest|verify_[a-z_]*signature",
        src,
    ):
        modes.add("signature")
        evidence.append("inline:signature header")
    if gated and not (modes - {"custom-key-header", "signature"}):
        modes.add("session")
        modes |= set(middleware_bearer)
    return modes, perms, evidence, gated, csrf


def auth_profile(callback, *, middleware_bearer: tuple = ()) -> dict:
    """Credential modes, permission, CSRF exemption and the evidence used.

    ``middleware_bearer`` are modes a host middleware adds to every
    session-gated view (e.g. ``jwt`` for a JWT-bearer-to-session shim).
    """
    kind, target = view_target(callback)
    if is_drf(callback):
        modes, perms, evidence, gated, csrf = _drf_profile(target, callback)
    else:
        modes, perms, evidence, gated, csrf = _django_profile(
            kind, target, callback, middleware_bearer
        )
    if not gated and not modes - {"custom-key-header"}:
        modes.add("none")
    return {
        "auth": sorted(modes),
        "permission": ",".join(dict.fromkeys(perms))
        or ("login" if gated else "public"),
        "csrf_exempt": csrf,
        "auth_evidence": evidence,
        "custom_key_header": "custom-key-header" in modes,
    }


__all__ = [
    "auth_profile",
    "chain",
    "classify_name",
    "decorator_names",
    "http_methods",
    "is_drf",
    "source",
    "view_target",
]
