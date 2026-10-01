"""CLI subcommand: ``scitex-sdk ui lint <path>``.

Walks ``<path>`` (file or directory tree) and prints UI-101..107
violations in the standard ``path:line:col [RULE-ID] message`` format
that `scitex-linter` and `flake8` use. Exit code 0 if no violations, 1
otherwise — letting CI gate on the lint cleanly.

Wired up by ``scitex_sdk.ui._cli:main`` as a ``click`` subcommand and
re-exported via the ``scitex-ui`` console script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .._cli_help import cli_help, examples as _examples, spec_command
from ._checker import scan_path
from ._rules import COVERAGE_GAPS, coverage_notice


def _emit_coverage_json() -> None:
    """Emit the coverage statement as a JSONL record.

    JSON consumers need the gap as much as humans do — arguably more,
    since a machine reading an empty violation stream has nothing else
    to tell it the scan was partial.
    """
    import json

    click.echo(
        json.dumps(
            {
                "kind": "coverage",
                "not_inspected": [
                    {"area": name, "detail": detail} for name, detail in COVERAGE_GAPS
                ],
            },
            ensure_ascii=False,
        )
    )


@click.command(
    name="lint",
    **spec_command(
        cli_help(
            summary="Lint a path against the scitex-sdk ui component rules.",
            description=(
                "Defaults to treating TARGET as a CONSUMER repo, where UI-104 "
                "fires on shell/primitive edits. Pass --treat-as-scitex-sdk ui when "
                "linting this package itself, where those edits are the point.",
                "Rule coverage is reported explicitly: gaps are printed rather "
                "than silently skipped, so a clean run means the rules ran, not "
                "that they were absent.",
            ),
            examples=_examples(
                ("{prog} ./src", "lint a consumer repo"),
                ("{prog} ./src --treat-as-scitex-ui", "lint scitex-sdk ui itself"),
            ),
            exit_codes=((0, "no violations"), (1, "violations found")),
        )
    ),
)
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
)
@click.option(
    "--treat-as-consumer/--treat-as-scitex-ui",
    "treat_as_consumer",
    default=True,
    show_default=True,
    help=(
        "Treat the target as a CONSUMER repo (default — UI-104 fires "
        "on shell/primitive edits) or as SCITEX-UI ITSELF (UI-104 "
        "suppressed — shell/primitive edits are allowed from inside "
        "scitex-ui)."
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit one JSON object per violation (one per line, JSONL).",
)
def lint(target: Path, treat_as_consumer: bool, as_json: bool) -> None:
    """Scan TARGET for scitex-sdk ui component-usage violations (UI-101..107).

    TARGET may be a directory or a single file. The walker recognises
    `.css`, `.html`, `.htm`, `.tsx`, `.jsx`, `.ts`, and `.js`; it
    skips `node_modules/`, `.venv/`, `.git/` etc. by default.

    Exit code is 0 when no violations are found, 1 otherwise.

    \b
    Example:
      $ scitex-sdk ui lint src/my_app/static/my_app/
      $ scitex-sdk ui lint --json src/my_app/static/my_app/ > violations.jsonl
      $ scitex-sdk ui lint --treat-as-scitex-sdk ui src/scitex_sdk/ui/   # ours own dev tree
    """
    violations = scan_path(target, treat_as_consumer=treat_as_consumer)
    if not violations:
        if as_json:
            _emit_coverage_json()
        else:
            click.echo(f"OK: {target} — no UI-1xx violations found.")
            # A clean run is exactly where a false sense of closure is
            # cheapest to acquire, so the gaps are loudest here.
            click.echo(f"\n{coverage_notice()}")
        sys.exit(0)
    if as_json:
        import json

        _emit_coverage_json()
        for v in violations:
            click.echo(
                json.dumps(
                    {
                        "rule": v.rule.id,
                        "severity": v.rule.severity,
                        "path": v.path,
                        "line": v.line,
                        "col": v.col,
                        "message": v.rule.message,
                        "suggestion": v.rule.suggestion,
                        "source_line": v.source_line,
                    },
                    ensure_ascii=False,
                )
            )
    else:
        for v in violations:
            click.echo(f"{v.path}:{v.line}:{v.col} [{v.rule.id}] {v.rule.message}")
        click.echo(
            f"\n{len(violations)} violation(s) found. "
            "See _skills/scitex-ui/40_component-usage-doctrine.md for fixes."
        )
        click.echo(f"\n{coverage_notice()}")
    sys.exit(1)


__all__ = ["lint"]
