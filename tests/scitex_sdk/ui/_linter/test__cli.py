"""Tests for ``scitex-ui lint`` — the CLI surface and its coverage notice.

The notice exists because "no violations found" is indistinguishable from
"nothing was looked at" unless the output says what it could not see.
scitex-dev made that a requirement on the EMITTED VERDICT rather than the
docs (2026-07-29), and STX-UI106 is a live example of the gap: it counts
``<option>`` tags in source, so a ``<select>`` populated at runtime is
invisible to it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from scitex_sdk.ui._linter._cli import lint
from scitex_sdk.ui._linter._rules import COVERAGE_GAPS

_CLEAN = "body { color: var(--stx-text); }\n"
# 20 options with no filter and no opt-out — fires STX-UI106.
_DIRTY = "<select>" + "".join(f"<option>{i}</option>" for i in range(20)) + "</select>"

_NOTICE = "NOT EVERYTHING WAS INSPECTED"


def _run(tmp_path: Path, name: str, body: str, *extra: str):
    (tmp_path / name).write_text(body)
    return CliRunner().invoke(lint, [str(tmp_path), *extra])


def _records(result) -> list[dict]:
    return [json.loads(line) for line in result.output.splitlines() if line.strip()]


def test_clean_run_exits_zero(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN)
    # Assert
    assert result.exit_code == 0


def test_clean_run_states_that_the_scan_was_partial(tmp_path: Path) -> None:
    # Arrange — a clean verdict is where false closure is cheapest to acquire.
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN)
    # Assert
    assert _NOTICE in result.output


def test_clean_run_names_the_rule_the_runtime_gap_affects(tmp_path: Path) -> None:
    # Arrange — naming the gap generically is not enough; the reader has to
    # learn that a JS-populated <select> is unseen by STX-UI106 specifically.
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN)
    # Assert
    assert "STX-UI106" in result.output


def test_violation_run_exits_one(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path
    # Act
    result = _run(target, "page.html", _DIRTY)
    # Assert
    assert result.exit_code == 1


def test_violation_run_also_states_that_the_scan_was_partial(tmp_path: Path) -> None:
    # Arrange — finding something does not imply completeness; a partial scan
    # that DID report still covers only what it can see.
    target = tmp_path
    # Act
    result = _run(target, "page.html", _DIRTY)
    # Assert
    assert _NOTICE in result.output


def test_at_least_one_gap_is_declared() -> None:
    # Arrange — the guard below parametrizes over COVERAGE_GAPS, so an EMPTY
    # corpus collects zero cases and pytest reports it as skipped rather than
    # failed. The check would then be gone while the suite still looked fine:
    # not a check anyone disabled, but a check whose subject was deleted out
    # from under it. Measured — emptying COVERAGE_GAPS gave "8 passed,
    # 1 skipped", and the skip was that guard.
    # Act
    declared = len(COVERAGE_GAPS)
    # Assert
    assert declared > 0, "COVERAGE_GAPS is empty — the per-gap guard below is vacuous"


@pytest.mark.parametrize("area", [area for area, _detail in COVERAGE_GAPS])
def test_every_declared_gap_reaches_the_output(tmp_path: Path, area: str) -> None:
    # Arrange — guards the notice against drifting out of sync with the data:
    # a gap added to COVERAGE_GAPS but never rendered is one the reader never
    # learns about, which is the defect this whole notice exists to remove.
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN)
    # Assert
    assert area in result.output


def test_json_mode_emits_exactly_one_coverage_record(tmp_path: Path) -> None:
    # Arrange — a machine reading an EMPTY violation stream has nothing else
    # to tell it the scan was partial, so JSON needs this most.
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN, "--json")
    # Assert
    assert len([r for r in _records(result) if r.get("kind") == "coverage"]) == 1


def test_json_coverage_record_carries_every_gap(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path
    # Act
    result = _run(target, "a.css", _CLEAN, "--json")
    coverage = [r for r in _records(result) if r.get("kind") == "coverage"][0]
    # Assert
    assert len(coverage["not_inspected"]) == len(COVERAGE_GAPS)


def test_json_mode_still_emits_violations(tmp_path: Path) -> None:
    # Arrange — the coverage record must not corrupt the JSONL contract.
    target = tmp_path
    # Act
    result = _run(target, "page.html", _DIRTY, "--json")
    # Assert
    assert any(r.get("rule") == "STX-UI106" for r in _records(result))


def test_json_mode_pairs_violations_with_the_coverage_record(tmp_path: Path) -> None:
    # Arrange — both must be present together; a violation stream without the
    # coverage line would again imply the scan was complete.
    target = tmp_path
    # Act
    result = _run(target, "page.html", _DIRTY, "--json")
    # Assert
    assert any(r.get("kind") == "coverage" for r in _records(result))
