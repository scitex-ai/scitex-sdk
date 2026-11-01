"""Executable native-edit and changed-file header ownership guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def check_payload(payload):
    """Inspect proposed editor contents or actual changed shell outputs."""
    from .ui._linter._header_contract import scan_headers

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
        if not path.is_relative_to(root):
            raise ValueError("Edited path is outside the tool repository")
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
            raise ValueError("Cannot enumerate changed source outside a Git repository")
        for args in (
            ["diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD"],
            ["ls-files", "--others", "--exclude-standard", "-z"],
        ):
            changed = subprocess.run(
                ["git", "-C", str(root), *args], capture_output=True, check=True
            )
            targets.update(root / p for p in changed.stdout.decode().split("\0") if p)
    else:
        return []
    return [
        f"PS-SDK-HEADER: {f.path}:{f.line}: {f.detail}"
        for f in scan_headers(root, overlays=overlays, targets=targets)
    ]


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
