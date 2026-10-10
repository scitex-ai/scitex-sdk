#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plugin-side filesystem jail contract (cooperative tier).

A leaf whose views read or write host files from caller-controlled paths
declares that fact in its own manifest under ``mount_policy``; the host
(scitex-hub's generic plugin mount, or any Django project) enforces the
declaration with the helpers here — no per-app host code::

    "mount_policy": {
      "login_required": true,
      "touches_files": true,
      "jail": {
        "scope": "user",
        "working_dir_param": "working_dir",
        "path_params": ["path", "recipe", "recipe_path"]
      }
    }

WHY THIS LIVES HERE. The hub used to contain each file-touching leaf with
bespoke per-app wrapper code (figrecipe's SITE-2 guard, writer's SITE-3
wrapper). Every new third-party/user app needed its own wrapper, and a
refactor could silently unwire one. The guard therefore moves plugin-side
as shared infrastructure: the leaf DECLARES its path-bearing channels
(query/body keys it joins to ``working_dir``), the SDK VALIDATES the
declaration and ENFORCES containment, and the host only supplies the two
facts the SDK cannot know — the requesting user's jail root and the
server-side working directory. A future app is contained with zero
per-app host code: declare it and the generic mount enforces it.

WHAT THE DECLARATION MEANS.

* ``touches_files`` — the leaf opts into the file-access contract. A
  file-touching plugin WITHOUT a ``jail`` block fails loudly at mount
  time (:func:`validate_mount_policy` raises :class:`LeafContractError`);
  plugins that never touch files omit both keys and mount exactly as
  before (absent key = open behaviour, back-compatible).
* ``jail.scope`` — ``"user"`` (the caller's own data root) or
  ``"project"`` (the caller's current project directory). CLOSED enum:
  a typo fails loud, never guesses.
* ``jail.working_dir_param`` — the query key carrying the working
  directory (default ``"working_dir"``). The wrapper OVERWRITES it from
  the server-side resolver; a caller-supplied value is discarded, never
  honoured.
* ``jail.path_params`` — query/body keys the leaf resolves RELATIVE TO
  ``working_dir`` (or opens verbatim when absolute). EVERY such key must
  be listed: ``pathlib``'s ``/`` DISCARDS the left operand when the
  right side is absolute, so an absolute value escapes a server-forced
  ``working_dir``; a relative ``../`` value climbs out. The single
  resolved-join + jail containment check closes both — but only for keys
  the leaf declared. An undeclared key is an unenforced channel: the
  mount-time bar cannot see it, so review a leaf's handlers against its
  ``path_params`` the way the hub's figrecipe guard enumerates its three
  channels.

WHAT STAYS LEAF-SIDE. Endpoint-gated body sinks whose base is NOT
``working_dir`` (figrecipe's ``api/compose`` PNG write, gallery
``template`` read, ``file://`` URL fetch) and URL-segment path sinks
(``api/file-content/<remainder>``) cannot be expressed as a key list.
The leaf keeps those checks in an ``extra_guard`` callable built on the
primitives here (:func:`is_in_jail`, :func:`resolve_against`), and the
wrapper invokes it after the generic channel check. See
:const:`FIGRECIPE_JAIL_REFERENCE` for the canonical split.

HOST OBLIGATIONS (two callbacks, dependency-injected like the hub's
``WorkingDirScopedView`` so this module never imports host code):

* ``get_jail_root(request)`` — the requesting user's jail root as
  ``str``/``Path`` (``None`` when unresolvable: anonymous, unknown
  user). A missing root fails closed (403), never open.
* ``resolve_working_dir(request)`` — the server-side working directory
  (current project dir) as ``str``/``Path``, or ``None`` when no
  project resolves. ``None`` with ``fail_closed=True`` (default) serves
  ``on_missing``; the caller's ``?working_dir=`` is NEVER consulted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from .plugins import LeafContractError

#: Manifest key carrying the whole plugin-mount contract.
MOUNT_POLICY_KEY = "mount_policy"

#: The two jail scopes. CLOSED enum: anything else fails loud.
JAIL_SCOPE_USER = "user"
JAIL_SCOPE_PROJECT = "project"
VALID_JAIL_SCOPES = (JAIL_SCOPE_USER, JAIL_SCOPE_PROJECT)

#: Default scope when ``jail: true`` shorthand is used. ``user`` is the
#: safe default: it contains to the caller's own data root, the
#: direction every existing hub check enforces.
DEFAULT_JAIL_SCOPE = JAIL_SCOPE_USER

#: Default query key carrying the working directory.
DEFAULT_WORKING_DIR_PARAM = "working_dir"

#: Canonical fail-closed body, byte-identical to the hub figrecipe
#: guard's so clients see one message across the migration.
FORBIDDEN_MESSAGE = "path is outside your workspace"

#: Reference declaration for figrecipe (card hub-figrecipe-leaf-move).
#: Query/body keys its dispatch joins to ``working_dir`` (or opens
#: verbatim when absolute); the compose/gallery/URL-segment sinks stay
#: leaf-side ``extra_guard`` checks built on :func:`is_in_jail`.
FIGRECIPE_JAIL_REFERENCE: Dict[str, Any] = {
    "scope": "user",
    "working_dir_param": "working_dir",
    "path_params": ("path", "recipe", "recipe_path"),
}

#: The full ``mount_policy`` block figrecipe adopts (reference — the
#: leaf copies this into its own manifest; kept here so the contract
#: and its first consumer are reviewed together).
FIGRECIPE_MOUNT_POLICY_REFERENCE: Dict[str, Any] = {
    "login_required": True,
    "touches_files": True,
    "jail": {
        "scope": "user",
        "working_dir_param": "working_dir",
        "path_params": ["path", "recipe", "recipe_path"],
    },
}


def jail_policy_of(manifest: Optional[Mapping[str, Any]]) -> Any:
    """Return the raw ``jail`` block from a manifest's ``mount_policy``.

    ``True`` shorthand means ``{"scope": <default>}``; absent/false/None
    means ``{}`` (no jail declared). Anything else is returned verbatim
    for :func:`normalize_jail_policy` to judge — including wrong types,
    which fail loud there rather than here.
    """
    if not manifest:
        return {}
    policy = manifest.get(MOUNT_POLICY_KEY, {})
    if not isinstance(policy, dict):
        # Not a jail question at all: validate_mount_policy() reports
        # the malformed mount_policy itself.
        return {}
    raw = policy.get("jail", {})
    if raw is True:
        return {"scope": DEFAULT_JAIL_SCOPE}
    if raw in (False, None):
        return {}
    return raw


def normalize_jail_policy(raw: Any, *, plugin: str = "plugin") -> Dict[str, Any]:
    """Validate a raw ``jail`` block and return its canonical form.

    Returns ``{"scope", "working_dir_param", "path_params"}`` with
    ``path_params`` as a tuple. ``True`` shorthand means the default
    scope. Raises :class:`LeafContractError`
    naming the plugin on ANY malformed value — typo'd scope, non-string
    working-dir param, non-list params, empty entries — so a bad
    declaration fails at mount/validation time, never deep in a request.
    """
    if raw is True:
        raw = {"scope": DEFAULT_JAIL_SCOPE}
    if isinstance(raw, bool) or raw is None:
        raise LeafContractError(
            f"{plugin}.mount_policy.jail must be an object "
            f"{{scope, working_dir_param?, path_params?}} (got {raw!r})"
        )
    if not isinstance(raw, Mapping):
        raise LeafContractError(
            f"{plugin}.mount_policy.jail must be an object "
            f"(got {type(raw).__name__}: {raw!r})"
        )
    scope = str(raw.get("scope", DEFAULT_JAIL_SCOPE)).strip().lower()
    if scope not in VALID_JAIL_SCOPES:
        raise LeafContractError(
            f"{plugin}.mount_policy.jail.scope must be one of "
            f"{VALID_JAIL_SCOPES} (got {raw.get('scope')!r})"
        )
    param = raw.get("working_dir_param", DEFAULT_WORKING_DIR_PARAM)
    if not isinstance(param, str) or not param.strip():
        raise LeafContractError(
            f"{plugin}.mount_policy.jail.working_dir_param must be a "
            f"non-empty string (got {param!r})"
        )
    params = raw.get("path_params", ())
    if isinstance(params, str) or not isinstance(params, (list, tuple)):
        raise LeafContractError(
            f"{plugin}.mount_policy.jail.path_params must be a list of "
            f"query/body key names (got {params!r})"
        )
    clean = []
    for entry in params:
        if not isinstance(entry, str) or not entry.strip():
            raise LeafContractError(
                f"{plugin}.mount_policy.jail.path_params entries must be "
                f"non-empty strings (got {entry!r})"
            )
        clean.append(entry.strip())
    return {
        "scope": scope,
        "working_dir_param": param.strip(),
        "path_params": tuple(clean),
    }


def validate_mount_policy(
    manifest: Optional[Mapping[str, Any]], *, plugin: str = "plugin"
) -> Dict[str, Any]:
    """Mount-time bar for a plugin manifest's ``mount_policy``.

    The host's generic mount calls this once per plugin at startup; it
    returns the normalized jail dict, or ``{}`` for plugins outside the
    file-access contract. It RAISES :class:`LeafContractError` when:

    * ``mount_policy`` is present but not an object;
    * ``touches_files`` is present but not a bool;
    * the plugin touches files (``touches_files: true``) but declares
      no ``jail`` block — the file-touching plugin without a jail
      policy fails loudly instead of mounting open;
    * the ``jail`` block is malformed (delegates to
      :func:`normalize_jail_policy`);
    * a ``jail`` is declared without ``login_required: true`` — a jailed
      mount needs an authenticated user to jail TO, and the host's login
      boundary is what provides it.

    Plugins that omit ``mount_policy`` entirely pass through with
    ``{}``: old leaves without declarations keep working unchanged.
    """
    if not manifest:
        return {}
    policy = manifest.get(MOUNT_POLICY_KEY, None)
    if policy is None:
        return {}
    if not isinstance(policy, dict):
        raise LeafContractError(
            f"{plugin}.mount_policy must be an object (got {policy!r})"
        )
    touches = policy.get("touches_files", False)
    if not isinstance(touches, bool):
        raise LeafContractError(
            f"{plugin}.mount_policy.touches_files must be true or false "
            f"(got {touches!r})"
        )
    raw = policy.get("jail", None)
    if raw in (None, False, {}):
        if touches:
            raise LeafContractError(
                f"{plugin} touches files (mount_policy.touches_files) but "
                f"declares no mount_policy.jail — declare the jail scope "
                f"and path_params (see scitex_sdk.app.jail) or drop "
                f"touches_files"
            )
        return {}
    jail = normalize_jail_policy(raw, plugin=plugin)
    if not policy.get("login_required", False):
        raise LeafContractError(
            f"{plugin} declares mount_policy.jail but not "
            f"mount_policy.login_required — a jailed mount must be "
            f"login-gated (the host enforces login_required at mount)"
        )
    return jail


def is_in_jail(target: Any, jail_root: Any) -> bool:
    """True iff ``target`` resolves inside ``jail_root`` (component-wise).

    ``Path.relative_to``, NOT a string prefix match: ``.../proj`` is a
    string prefix of the sibling ``.../proj-secret``, so ``startswith``
    would admit ``proj/../proj-secret/x`` and leak cross-tenant.
    Unresolvable inputs and a missing root fail closed (``False``).
    """
    if target is None or jail_root is None:
        return False
    try:
        Path(target).resolve().relative_to(Path(jail_root).resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def resolve_against(base: Any, value: str) -> Path:
    """Join ``value`` to ``base`` and resolve, preserving attack shape.

    Deliberately plain ``(base / value).resolve()``: ``pathlib``'s ``/``
    DISCARDS ``base`` when ``value`` is absolute, and ``..`` climbs out
    — both land OUTSIDE the jail, where the single containment check
    (:func:`is_in_jail`) rejects them. A helper that stripped absolutes
    first would hide the escape instead of closing it.
    """
    return (Path(base) / value).resolve()


def iter_path_candidates(
    query: Mapping[str, Any],
    body: Mapping[str, Any],
    path_params: Tuple[str, ...],
    working_dir: Any,
):
    """Yield ``(channel, key, value, candidate)`` for declared params.

    ``channel`` is ``"query"`` or ``"body"``. Values that are not
    non-empty strings are skipped (the leaf would reject them itself;
    there is no path to contain). With a server-side ``working_dir``,
    candidates are ``(working_dir / value).resolve()``; without one
    (defensive only — the wrapper fails closed before this) the raw
    value resolves against the process cwd and STILL faces the jail
    check, so absolute/``..`` values fail closed rather than open.
    """
    for key in path_params:
        for channel, source in (("query", query), ("body", body)):
            try:
                value = source.get(key)
            except AttributeError:
                continue
            if not isinstance(value, str) or not value:
                continue
            if working_dir is not None:
                candidate = resolve_against(working_dir, value)
            else:
                candidate = Path(value).resolve()
            yield channel, key, value, candidate


def first_escape(
    query: Mapping[str, Any],
    body: Mapping[str, Any],
    *,
    path_params: Tuple[str, ...],
    working_dir: Any,
    jail_root: Any,
) -> Optional[Tuple[str, str]]:
    """Return the first ``(key, value)`` escaping ``jail_root``, or None.

    Pure (no Django, no host imports): the SAME predicate serves the
    request wrapper, host middleware, and tests. ``None`` (no block)
    ONLY when every declared candidate is contained; the first escape
    fails closed.
    """
    for _channel, key, value, candidate in iter_path_candidates(
        query or {}, body or {}, tuple(path_params or ()), working_dir
    ):
        if not is_in_jail(candidate, jail_root):
            return key, value
    return None


def parse_json_body(request) -> dict:
    """Return the request's JSON body as a dict (``{}`` otherwise).

    ``{}`` for GET, absent bodies, non-JSON payloads, and non-object
    JSON — the guard inspects what the leaf would read, and the leaf
    reads objects.
    """
    if getattr(request, "method", "GET") == "GET":
        return {}
    raw = getattr(request, "body", b"")
    if not raw:
        return {}
    import json

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


class JailScopedView:
    """Wrap a leaf view: server-side ``working_dir`` + jail containment.

    The SDK-side twin of the hub's ``WorkingDirScopedView``, with the
    host facts dependency-injected so this module never imports host
    code:

      ``downstream(request, *args, **kwargs)`` — the leaf view.
      ``get_jail_root(request)`` — requesting user's jail root
          (``str``/``Path``; ``None`` fails closed with 403).
      ``resolve_working_dir(request)`` — server-side project directory
          (``str``/``Path``) or ``None`` when no project resolves.
      ``jail`` — raw ``mount_policy.jail`` block (or ``True``); typos
          fail loud at construction via :func:`normalize_jail_policy`.
      ``on_missing(request)`` — fail-closed response when no working
          directory resolves and ``fail_closed`` is set.
      ``extra_guard(request, body, *args, **kwargs)`` — optional
          leaf-specific sinks (endpoint-gated body keys, URL-segment
          paths) returning a response to short-circuit, or ``None``.
          Runs AFTER the generic channel check; receives the SAME
          positional args as ``downstream`` (notably a URL
          ``<path:endpoint>`` capture).
      ``forbidden(request, key, value)`` — escape response builder;
          defaults to the canonical 403 JSON.

    This object holds NO authentication logic — the host applies its
    login boundary outside it (and ``validate_mount_policy`` refuses a
    jailed mount without one), so an anonymous request never reaches
    here; a missing jail root STILL fails closed regardless.
    """

    def __init__(
        self,
        downstream: Callable,
        *,
        get_jail_root: Callable,
        resolve_working_dir: Callable,
        jail: Any = True,
        on_missing: Optional[Callable] = None,
        extra_guard: Optional[Callable] = None,
        forbidden: Optional[Callable] = None,
        fail_closed: bool = True,
        plugin: str = "plugin",
    ):
        self.downstream = downstream
        self.get_jail_root = get_jail_root
        self.resolve_working_dir = resolve_working_dir
        self.jail = normalize_jail_policy(jail, plugin=plugin)
        self.on_missing = on_missing
        self.extra_guard = extra_guard
        self.forbidden = forbidden or self._default_forbidden
        self.fail_closed = fail_closed
        self.plugin = plugin

    @staticmethod
    def _default_forbidden(request, key, value):
        try:
            from django.http import JsonResponse
        except ImportError as exc:
            raise ImportError(
                "scitex_sdk.app.jail needs django: pip install scitex-sdk[all]"
            ) from exc
        return JsonResponse({"error": FORBIDDEN_MESSAGE}, status=403)

    def _forbid(self, request, key, value):
        import logging

        logging.getLogger(__name__).warning(
            "[jail] rejecting out-of-jail %s=%r for user %s",
            key,
            value,
            getattr(getattr(request, "user", None), "username", "?"),
        )
        return self.forbidden(request, key, value)

    def __call__(self, request, *args, **kwargs):
        jail_root = self.get_jail_root(request)
        if jail_root is None:
            return self._forbid(request, "jail", "")

        working_dir = self.resolve_working_dir(request)
        param = self.jail["working_dir_param"]
        if working_dir is not None:
            working_dir = str(working_dir)
            try:
                params = request.GET.copy()
            except AttributeError as exc:
                raise LeafContractError(
                    f"{self.plugin}: JailScopedView needs a Django request "
                    f"with a mutable GET (got {type(request.GET).__name__})"
                ) from exc
            if params.get(param) and params.get(param) != working_dir:
                import logging

                logging.getLogger(__name__).warning(
                    "[jail] discarding client-supplied %s from user %s "
                    "(server-side tenancy only)",
                    param,
                    getattr(getattr(request, "user", None), "username", "?"),
                )
            params[param] = working_dir  # OVERWRITE, never default
            request.GET = params
        elif self.fail_closed:
            if self.on_missing is None:  # pragma: no cover - misconfiguration
                raise RuntimeError(
                    "JailScopedView(fail_closed=True) needs on_missing"
                )
            return self.on_missing(request)

        body = parse_json_body(request)
        escape = first_escape(
            request.GET,
            body,
            path_params=self.jail["path_params"],
            working_dir=working_dir,
            jail_root=jail_root,
        )
        if escape is not None:
            key, value = escape
            return self._forbid(request, key, value)

        if self.extra_guard is not None:
            blocked = self.extra_guard(request, body, *args, **kwargs)
            if blocked is not None:
                return blocked

        return self.downstream(request, *args, **kwargs)


__all__ = [
    "DEFAULT_JAIL_SCOPE",
    "DEFAULT_WORKING_DIR_PARAM",
    "FIGRECIPE_JAIL_REFERENCE",
    "FIGRECIPE_MOUNT_POLICY_REFERENCE",
    "FORBIDDEN_MESSAGE",
    "JAIL_SCOPE_PROJECT",
    "JAIL_SCOPE_USER",
    "MOUNT_POLICY_KEY",
    "VALID_JAIL_SCOPES",
    "JailScopedView",
    "first_escape",
    "is_in_jail",
    "iter_path_candidates",
    "jail_policy_of",
    "normalize_jail_policy",
    "parse_json_body",
    "resolve_against",
    "validate_mount_policy",
]

# EOF
