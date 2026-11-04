"""Executable native-edit and changed-file header ownership guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _source_changes(payload, *, suffixes=None, include_deletions=False):
    """Read proposed or changed files without mutating the project."""

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        text=True,
    )
    root = Path(result.stdout.strip()) if result.returncode == 0 else cwd
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or payload.get("arguments") or {}
    filename = data.get("file_path") or data.get("path")
    overlays = {}
    targets = set()
    if tool in {"Write", "write_file", "Edit", "MultiEdit", "patch"} and filename:
        path = Path(filename)
        path = (path if path.is_absolute() else cwd / path).resolve()
        if path.suffix.lower() not in (suffixes or {".css", ".html", ".htm", ".tsx", ".jsx"}):
            return None
        # Native clients can run from HOME while editing an absolute repo
        # path. Resolve the edited project's scope, never walk all HOME.
        directory = path.parent
        while not directory.is_dir() and directory != directory.parent:
            directory = directory.parent
        project = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if project.returncode == 0:
            root = Path(project.stdout.strip())
        else:
            root = next(
                (
                    p
                    for p in (directory, *directory.parents)
                    if (p / "pyproject.toml").is_file()
                ),
                directory,
            )
        if tool in {"Write", "write_file"}:
            text = data["content"]
        else:
            text = path.read_text(encoding="utf-8")
            for edit in data.get("edits", [data]):
                old = edit.get("old_string", "")
                if not old or old not in text:
                    raise ValueError("Cannot verify proposed edit")
                text = text.replace(
                    old,
                    edit.get("new_string", ""),
                    -1 if edit.get("replace_all") else 1,
                )
        overlays[path] = text
        targets.add(path)
    elif tool in {"Bash", "terminal", "apply_patch"}:
        if result.returncode:
            # Source hooks cover project changes. Host commands outside a repo
            # have no source baseline; the project auditor/CI owns that boundary.
            return None
        diff_filter = "ACMRD" if include_deletions else "ACMR"
        for args in (
            ["diff", "--name-only", f"--diff-filter={diff_filter}", "-z"],
            ["diff", "--cached", "--name-only", f"--diff-filter={diff_filter}", "-z"],
            ["ls-files", "--others", "--exclude-standard", "-z"],
        ):
            changed = subprocess.run(
                ["git", "-C", str(root), *args], capture_output=True, check=True
            )
            targets.update(root / p for p in changed.stdout.decode().split("\0") if p)
    else:
        return None
    return root, overlays, targets


def check_payload(payload):
    """Inspect proposed editor contents or actual changed shell outputs."""
    from .ui._linter._filter_contract import scan_filters
    from .ui._linter._header_contract import scan_headers
    from .ui._linter._shell_contract import scan_shell

    changed = _source_changes(payload)
    if changed is None:
        return []
    root, overlays, targets = changed
    return (
        [
            f"PS-SDK-HEADER: {f.path}:{f.line}: {f.detail}"
            for f in scan_headers(root, overlays=overlays, targets=targets)
        ]
        + [
            f"PS-SDK-FILTER: {f.path}:{f.line}: {f.detail}"
            for f in scan_filters(root, overlays=overlays, targets=targets)
        ]
        + [
            f"PS-SDK-SHELL: {f.path}:{f.line}: {f.detail}"
            for f in scan_shell(root, overlays=overlays, targets=targets)
        ]
    )


def check_scrollbar_payload(payload):
    """Adapt the existing scrollbar warning to the native payload protocol."""
    from .ui._linter._checker import _scan_css
    from .ui._linter._rules import build_rules

    changed = _source_changes(payload)
    if changed is None:
        return []
    _, overlays, targets = changed
    findings = []
    for path in targets:
        if path.suffix.lower() != ".css":
            continue
        text = overlays[path] if path in overlays else path.read_text(encoding="utf-8")
        for finding in _scan_css(path, text.splitlines(), build_rules()):
            if finding.rule.id in {"STX-UI105", "STX-UI115"}:
                findings.append(
                    f"{finding.rule.id}: {finding.path}:{finding.line}: {finding.rule.message}"
                )
    return findings


def main():
    """Return hook refusal status 2 when verification fails or finds a fork."""
    import scitex_logging as logging

    try:
        findings = check_payload(json.load(sys.stdin))
    except (
        ImportError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.CalledProcessError,
    ) as exc:
        findings = [f"PS-SDK-HEADER: verification failed ({type(exc).__name__})"]
    for finding in findings:
        logging.getLogger(__name__).error(finding)
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
