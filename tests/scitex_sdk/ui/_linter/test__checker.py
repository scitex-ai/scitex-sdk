"""Tests for the file-tree walker emitting UI-101..106 UIViolations.

No mocks — fixture files written via tmp_path so each test exercises the
real regex + walker code paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scitex_sdk.ui._linter._checker import scan_path


# --------------------------------------------------------------------------- #
# UI-101 — vanilla <select> without data-app-themed                            #
# --------------------------------------------------------------------------- #


def test_ui101_flags_vanilla_select_in_tsx(tmp_path: Path) -> None:
    # Arrange
    tsx = tmp_path / "Filter.tsx"
    tsx.write_text(
        'export const Filter = () => (\n  <select name="kind">\n    <option>a</option>\n  </select>\n);\n'
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI101" in ids


def test_ui101_skips_select_with_data_app_themed_attr(tmp_path: Path) -> None:
    # Arrange
    tsx = tmp_path / "Filter.tsx"
    tsx.write_text(
        '<select name="kind" data-app-themed="true">\n  <option>a</option>\n</select>\n'
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI101" for v in violations)


def test_ui101_skips_select_in_skip_dir_node_modules(tmp_path: Path) -> None:
    # Arrange — vendored deps under node_modules must be ignored entirely.
    nm = tmp_path / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "vendor.tsx").write_text("<select><option /></select>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


# --------------------------------------------------------------------------- #
# UI-102 — raw hex / rgb in app CSS                                            #
# --------------------------------------------------------------------------- #


def test_ui102_flags_raw_hex_color(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text("body { background: #112233; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI102" in ids


def test_ui102_skips_var_only_css(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text("body { background: var(--bg-page); color: var(--text-primary); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


def test_ui102_flags_rgb_literal(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "x.css"
    css.write_text("a { color: rgb(255, 128, 0); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI102" for v in violations)


def test_ui102_skips_hex_in_comment(tmp_path: Path) -> None:
    # Arrange — comments shouldn't trigger; they're not active style.
    css = tmp_path / "x.css"
    css.write_text("/* historical: was #112233 */\nbody { color: var(--text); }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


# --------------------------------------------------------------------------- #
# UI-103 — scitex-ui shell fingerprint copied into consumer CSS                #
# --------------------------------------------------------------------------- #


def test_ui103_flags_stx_shell_sidebar_selector(tmp_path: Path) -> None:
    # Arrange — consumer copied a shell selector into their own CSS.
    css = tmp_path / "board.css"
    css.write_text(".stx-shell-sidebar { padding: 1rem; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI103" for v in violations)


# --------------------------------------------------------------------------- #
# UI-104 — consumer-side modifications to shell/primitives layout             #
# --------------------------------------------------------------------------- #


def test_ui104_flags_consumer_css_under_shell_path(tmp_path: Path) -> None:
    # Arrange — consumer repo has a CSS file living under the shell tree.
    shell_dir = tmp_path / "scitex_sdk" / "ui" / "css" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "consumer_override.css").write_text(".app-shell { display: grid; }\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=True)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI104" in ids


def test_ui104_suppressed_when_running_inside_scitex_ui_itself(
    tmp_path: Path,
) -> None:
    # Arrange — same path, but scitex-ui's own dev tree may edit it.
    shell_dir = tmp_path / "scitex_sdk" / "ui" / "css" / "shell"
    shell_dir.mkdir(parents=True)
    (shell_dir / "theme.css").write_text("body { color: var(--text); }\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=False)

    # Assert
    assert all(v.rule.id != "STX-UI104" for v in violations)


# --------------------------------------------------------------------------- #
# UI-105 — raw color literal inside a scrollbar rule                          #
# --------------------------------------------------------------------------- #


def test_ui105_flags_raw_hex_in_webkit_scrollbar_thumb(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text(
        ".stx-todo-board ::-webkit-scrollbar-thumb {\n  background: #6a40a8;\n}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI105" in ids


def test_ui105_skips_scrollbar_thumb_using_var(tmp_path: Path) -> None:
    # Arrange — the OPERATOR-APPROVED pattern: local var backed by token.
    css = tmp_path / "board.css"
    css.write_text(
        ":root { --stx-scrollbar-thumb: var(--workspace-border-default); }\n"
        ".stx-todo-board ::-webkit-scrollbar-thumb {\n"
        "  background: var(--stx-scrollbar-thumb);\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI105" for v in violations)


def test_ui105_flags_scrollbar_color_declaration_with_raw_rgb(
    tmp_path: Path,
) -> None:
    # Arrange — Firefox-side declaration; same rule applies.
    css = tmp_path / "x.css"
    css.write_text(
        ".my-app { scrollbar-color: rgb(106, 64, 168) rgb(240, 240, 240); }\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI105" for v in violations)


# --------------------------------------------------------------------------- #
# Smoke + invariants                                                          #
# --------------------------------------------------------------------------- #


def test_scan_path_returns_empty_for_clean_consumer_tree(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "board.css"
    css.write_text(
        ":root { --my-bg: var(--bg-page); }\n"
        ".my-app { background: var(--my-bg); color: var(--text-primary); }\n"
    )
    tsx = tmp_path / "App.tsx"
    tsx.write_text("import { Dropdown } from 'scitex_ui';\nexport default Dropdown;\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert violations == []


def test_scan_path_accepts_single_file_returns_one_violation(
    tmp_path: Path,
) -> None:
    # Arrange
    css = tmp_path / "x.css"
    css.write_text("body { color: #ff0000; }\n")
    # Act
    violations = scan_path(css)
    # Assert
    assert len(violations) == 1


def test_scan_path_accepts_single_file_violation_carries_correct_rule_id(
    tmp_path: Path,
) -> None:
    # Arrange — same single-file scan as above but assert the rule id only.
    css = tmp_path / "x.css"
    css.write_text("body { color: #ff0000; }\n")
    # Act
    violations = scan_path(css)
    # Assert
    assert violations[0].rule.id == "STX-UI102"


def test_violation_carries_correct_line_number(tmp_path: Path) -> None:
    # Arrange — line 3 carries the offender.
    css = tmp_path / "x.css"
    css.write_text(
        "body { color: var(--text); }\n"
        "main { padding: 1rem; }\n"
        "footer { background: #abcdef; }\n"
    )
    # Act
    violations = scan_path(css)
    # Assert
    assert violations[0].line == 3


def test_violation_carries_source_line_containing_offender(tmp_path: Path) -> None:
    # Arrange — same fixture; this guards the source_line capture path.
    css = tmp_path / "x.css"
    css.write_text(
        "body { color: var(--text); }\n"
        "main { padding: 1rem; }\n"
        "footer { background: #abcdef; }\n"
    )
    # Act
    violations = scan_path(css)
    # Assert
    assert "#abcdef" in violations[0].source_line


# --------------------------------------------------------------------------- #
# UI-106 — a long native <select> with no way to narrow it                     #
#                                                                              #
# The operator sent a screenshot of a 14-item project picker with no filter    #
# and asked whether "always put a fuzzy filter on a list like this" could be   #
# ENFORCED rather than merely stated. Most of it cannot — whether a given list #
# needs a filter is a UX call. This slice can, because it is a countable       #
# property of the markup.                                                      #
#                                                                              #
# The threshold matches Dropdown's DEFAULT_FILTER_THRESHOLD on purpose: a lint #
# disagreeing with the component it recommends is advice nobody can satisfy.   #
# --------------------------------------------------------------------------- #


def _options(count: int) -> str:
    return "".join(f'<option value="{i}">item {i}</option>' for i in range(count))


def _scan_markup(tmp_path: Path, markup: str) -> list[str]:
    page = tmp_path / "page.html"
    page.write_text(markup)
    return [v.rule.id for v in scan_path(page)]


@pytest.mark.parametrize("count", [9, 14, 40])
def test_ui106_flags_select_longer_than_the_threshold(
    tmp_path: Path, count: int
) -> None:
    # Arrange
    markup = f"<select id='f-agent'>{_options(count)}</select>"
    # Act
    fired = _scan_markup(tmp_path, markup)
    # Assert
    assert "STX-UI106" in fired, (
        f"a {count}-option native select was not flagged; past ~8 entries the "
        "native widget offers only first-character type-to-jump"
    )


@pytest.mark.parametrize("count", [0, 3, 8])
def test_ui106_leaves_short_select_alone(tmp_path: Path, count: int) -> None:
    # Arrange — a deliberately short action menu must not be nagged, or the
    # rule gets muted repo-wide and stops protecting the long ones.
    markup = f"<select>{_options(count)}</select>"
    # Act
    fired = _scan_markup(tmp_path, markup)
    # Assert
    assert "STX-UI106" not in fired, f"{count} options should not fire UI106"


@pytest.mark.parametrize("attr", ["data-no-combobox='1'", "data-stx-combobox='1'"])
def test_ui106_honours_explicit_opt_out(tmp_path: Path, attr: str) -> None:
    # Arrange — some long selects are genuinely fine (an ordered list scrolled
    # by position rather than searched by name), and one already enhanced must
    # not be told to enhance itself.
    markup = f"<select {attr}>{_options(20)}</select>"
    # Act
    fired = _scan_markup(tmp_path, markup)
    # Assert
    assert "STX-UI106" not in fired, f"{attr} must suppress the rule"


# --------------------------------------------------------------------------- #
# UI-107 — root-anchored API path literal in client code                       #
#                                                                             #
# Every exemption below is here because the rule's FIRST measured run would   #
# otherwise have been wrong: scitex-ui's own two grep hits were both comments, #
# and one was the docstring for apiUrl — the very fix UI-107 recommends.      #
# --------------------------------------------------------------------------- #


def _ui107(tmp_path: Path, name: str, body: str) -> list[str]:
    (tmp_path / name).write_text(body)
    return [v.rule.id for v in scan_path(tmp_path)]


def test_ui107_flags_a_root_anchored_api_literal(tmp_path: Path) -> None:
    # Arrange — correct standalone, silently wrong once mounted under a prefix.
    body = 'await fetch("/api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_flags_a_template_literal_too(tmp_path: Path) -> None:
    # Arrange — measured in scitex-writer: the real-world form is a backtick
    # template literal, not a plain string, so a quote-only pattern would have
    # missed the actual population.
    body = "await fetch(`/api/pdf?doc=${encodeURIComponent(d)}`);\n"
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_flags_the_hub_prefix_written_by_hand(tmp_path: Path) -> None:
    # Arrange — hardcoding the EMBEDDED prefix is the mirror-image bug: it
    # works on the hub and breaks standalone.
    body = 'await fetch("/apps/u/writer/api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_does_not_flag_the_fix_it_recommends(tmp_path: Path) -> None:
    # Arrange — THE exemption that decides whether anyone keeps this rule on.
    # apiUrl("/api/items") IS the remedy and contains the flagged pattern; a
    # rule that fires on its own remedy tells a fully-migrated app it still
    # has violations.
    body = 'import { apiUrl } from "@scitex/sdk/ui/ts/_base";\nawait fetch(apiUrl("/api/items"));\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_does_not_flag_a_line_comment(tmp_path: Path) -> None:
    # Arrange — measured 2026-07-30: both of scitex-ui's own matches were
    # comments. A grep-shaped rule indicts documentation.
    body = '// await fetch("/api/items");  // the old way\nexport const x = 1;\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_does_not_flag_a_docstring_continuation_line(tmp_path: Path) -> None:
    # Arrange — the exact shape of scitex-ui's own two hits: a `*`-prefixed
    # JSDoc body line, one of which documents apiUrl itself.
    body = '/**\n * `apiUrl("/api/items")` -> "/apps/u/writer/api/items"\n */\nexport const x = 1;\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_severity_is_error(tmp_path: Path) -> None:
    # Arrange — error is only defensible because the measured population was
    # 12 literals across 3 repos. A noisier rule would have to be a warning.
    (tmp_path / "client.ts").write_text('fetch("/api/x");\n')
    # Act
    sev = [v.rule.severity for v in scan_path(tmp_path) if v.rule.id == "STX-UI107"]
    # Assert
    assert sev == ["error"]


def test_ui107_reports_the_offending_line_number(tmp_path: Path) -> None:
    # Arrange — the rule scans per-line precisely so the exemptions are
    # meaningful; that must also give an exact location, not a file-level nag.
    (tmp_path / "client.ts").write_text('const a = 1;\nconst b = 2;\nfetch("/api/x");\n')
    # Act
    lines = [v.line for v in scan_path(tmp_path) if v.rule.id == "STX-UI107"]
    # Assert
    assert lines == [3]


def test_ui107_does_not_flag_a_relative_path(tmp_path: Path) -> None:
    # Arrange — a relative path already survives being mounted anywhere, so
    # flagging it would be advice with no defect behind it.
    body = 'await fetch("api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired
