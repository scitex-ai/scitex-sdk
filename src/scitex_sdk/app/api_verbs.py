#!/usr/bin/env python3
"""API-V003: action verbs come from the canonical SciTeX verb catalogue.

A REST action (``POST <resource>[/{id}]/<verb>``) and its MCP tool reuse the
vocabulary the CLIs already use (scitex-dev doctrine §1d,
``06_noun-verb-catalog.md`` and ``21_noun-verb-vocabulary.md``), so a client
that learned ``validate`` in one package never meets ``check`` or ``verify``
for the same meaning in the next.

A verb outside the catalogue needs a justified entry under ``verb_exceptions:``
in the package's ``.scitex/dev/cli-audit-dict.yaml``: the same key, file and
``# why`` rule the scitex-dev CLI audit reads, so one entry covers a verb on
both surfaces. Search is never an action: it is ``list`` with ``q``.

Stdlib only. The dictionary is read with a line parser for the one key, since
the SDK's base install carries no YAML library.
"""

from __future__ import annotations

import re
from pathlib import Path

from .api_ops import CRUD_VERBS

#: The §1d canonical and recommended transitive verbs, minus the CRUD verbs
#: (fixed by API-V001, never actions), minus the "avoid synonyms" column
#: (``verify``, ``check``, ``edit``, ``set``, ``reconcile``, ``refresh`` and the
#: rest) and minus ``search`` and ``show`` (an API reads with ``list``/``get``).
CANONICAL_ACTION_VERBS = frozenset(
    {
        # read
        "find",
        "describe",
        "inspect",
        "diff",
        "tail",
        # create / write
        "add",
        "init",
        "generate",
        "scaffold",
        "clone",
        "copy",
        "import",
        "register",
        # modify
        "rename",
        "move",
        "merge",
        "patch",
        "reset",
        "restore",
        "rollback",
        # delete
        "remove",
        "purge",
        "clean",
        "archive",
        "revoke",
        # lifecycle
        "start",
        "stop",
        "restart",
        "pause",
        "resume",
        "enable",
        "disable",
        "install",
        "uninstall",
        # release / deploy
        "build",
        "compile",
        "publish",
        "deploy",
        "tag",
        "ship",
        "submit",
        # I/O
        "load",
        "save",
        "read",
        "write",
        "fetch",
        "download",
        "upload",
        "export",
        "convert",
        "render",
        "parse",
        # validate
        "validate",
        "test",
        "lint",
        "format",
        "audit",
        "benchmark",
        # sync / state
        "sync",
        "pull",
        "push",
        "commit",
        "stash",
        "apply",
        # communication
        "send",
        "notify",
        "broadcast",
        "subscribe",
        # terminal states
        "done",
        "close",
        # API-J001 names the job action ``cancel`` explicitly.
        "cancel",
    }
)

#: Verbs that are never an action, with what to use instead.
REFUSED_ACTION_VERBS = {
    "search": "list with a q parameter (01-rules API-V003)",
    "show": "get",
    "verify": "validate",
    "check": "validate",
    "edit": "update",
    "modify": "update",
    "set": "update",
    "new": "create",
    "make": "create",
    "rm": "delete",
    "drop": "delete",
    "destroy": "delete",
    "reconcile": "sync",
    "refresh": "sync",
}

DICT_RELPATH = Path(".scitex", "dev", "cli-audit-dict.yaml")
_KEY = "verb_exceptions"
_ENTRY_RE = re.compile(r"""^\s*-\s*['"]?([A-Za-z0-9_-]+)['"]?\s*(#.*)?$""")


def read_verb_exceptions(path) -> dict:
    """``{verb: has_why}`` from the ``verb_exceptions:`` list of one dictionary.

    Missing file: no exceptions. Each entry's line must carry an inline
    ``# why`` comment; the value records whether it does.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    out: dict = {}
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[:1].isspace() and not line.startswith("-"):
            inside = line.split(":", 1)[0].strip() == _KEY
            continue
        if inside:
            match = _ENTRY_RE.match(line)
            if match:
                comment = match.group(2) or ""
                out[match.group(1).lower()] = "# why" in comment
    return out


def find_dictionary(start=None):
    """The package dictionary of the project containing ``start`` (or cwd).

    Walks up to the first directory with a ``pyproject.toml`` and returns its
    ``.scitex/dev/cli-audit-dict.yaml`` path (which may not exist), or None.
    """
    here = Path(start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        if (directory / "pyproject.toml").is_file():
            return directory / DICT_RELPATH
    return None


def verb_violations(ops, exceptions: dict) -> list:
    """``(rule, operation_id, message)`` for every off-catalogue action verb.

    ``exceptions`` is :func:`read_verb_exceptions` output. A compound action
    (``read-metadata``) is judged by its verb-first head token, as §1d spells
    compounds; an exception may name the whole action or its head.
    """
    out = []
    for op in ops:
        verb = op.verb
        if verb in CRUD_VERBS:
            continue
        head = verb.split("-", 1)[0]
        entry = verb if verb in exceptions else head if head in exceptions else None
        if entry is not None:
            if not exceptions[entry]:
                out.append(
                    (
                        "API-V003",
                        op.operation_id,
                        f"verb_exceptions entry {entry!r} lacks an inline '# why' "
                        "justification",
                    )
                )
            continue
        if head in REFUSED_ACTION_VERBS:
            out.append(
                (
                    "API-V003",
                    op.operation_id,
                    f"action verb {verb!r} is a non-canonical synonym; use "
                    f"{REFUSED_ACTION_VERBS[head]}",
                )
            )
        elif head not in CANONICAL_ACTION_VERBS:
            out.append(
                (
                    "API-V003",
                    op.operation_id,
                    f"action verb {verb!r} is not in the canonical verb catalogue; "
                    "pick one from it or justify it under verb_exceptions: in "
                    f"{DICT_RELPATH.as_posix()} with a '# why' comment",
                )
            )
    return out


__all__ = [
    "CANONICAL_ACTION_VERBS",
    "DICT_RELPATH",
    "REFUSED_ACTION_VERBS",
    "find_dictionary",
    "read_verb_exceptions",
    "verb_violations",
]

# EOF
