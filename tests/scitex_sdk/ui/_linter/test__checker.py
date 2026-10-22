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
    # Arrange
    # vendored deps under node_modules must be ignored entirely.
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
    # Arrange
    # comments shouldn't trigger; they're not active style.
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
    # Arrange
    # consumer copied a shell selector into their own CSS.
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
    # Arrange
    # consumer repo has a CSS file living under the shell tree.
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
    # Arrange
    # same path, but scitex-ui's own dev tree may edit it.
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
    # Arrange
    # the OPERATOR-APPROVED pattern: local var backed by token.
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
    # Arrange
    # Firefox-side declaration; same rule applies.
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
    # Arrange
    # same single-file scan as above but assert the rule id only.
    css = tmp_path / "x.css"
    css.write_text("body { color: #ff0000; }\n")
    # Act
    violations = scan_path(css)
    # Assert
    assert violations[0].rule.id == "STX-UI102"


def test_violation_carries_correct_line_number(tmp_path: Path) -> None:
    # Arrange
    # line 3 carries the offender.
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
    # Arrange
    # same fixture; this guards the source_line capture path.
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
    # Arrange
    # a deliberately short action menu must not be nagged, or the
    # rule gets muted repo-wide and stops protecting the long ones.
    markup = f"<select>{_options(count)}</select>"
    # Act
    fired = _scan_markup(tmp_path, markup)
    # Assert
    assert "STX-UI106" not in fired, f"{count} options should not fire UI106"


@pytest.mark.parametrize("attr", ["data-no-combobox='1'", "data-stx-combobox='1'"])
def test_ui106_honours_explicit_opt_out(tmp_path: Path, attr: str) -> None:
    # Arrange
    # some long selects are genuinely fine (an ordered list scrolled
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
    # Arrange
    # correct standalone, silently wrong once mounted under a prefix.
    body = 'await fetch("/api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_flags_a_template_literal_too(tmp_path: Path) -> None:
    # Arrange
    # measured in scitex-writer: the real-world form is a backtick
    # template literal, not a plain string, so a quote-only pattern would have
    # missed the actual population.
    body = "await fetch(`/api/pdf?doc=${encodeURIComponent(d)}`);\n"
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_flags_the_hub_prefix_written_by_hand(tmp_path: Path) -> None:
    # Arrange
    # hardcoding the EMBEDDED prefix is the mirror-image bug: it
    # works on the hub and breaks standalone.
    body = 'await fetch("/apps/u/writer/api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" in fired


def test_ui107_does_not_flag_the_fix_it_recommends(tmp_path: Path) -> None:
    # Arrange
    # THE exemption that decides whether anyone keeps this rule on.
    # apiUrl("/api/items") IS the remedy and contains the flagged pattern; a
    # rule that fires on its own remedy tells a fully-migrated app it still
    # has violations.
    body = 'import { apiUrl } from "@scitex/sdk/ui/ts/_base";\nawait fetch(apiUrl("/api/items"));\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_does_not_flag_a_line_comment(tmp_path: Path) -> None:
    # Arrange
    # measured 2026-07-30: both of scitex-ui's own matches were
    # comments. A grep-shaped rule indicts documentation.
    body = '// await fetch("/api/items");  // the old way\nexport const x = 1;\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_does_not_flag_a_docstring_continuation_line(tmp_path: Path) -> None:
    # Arrange
    # the exact shape of scitex-ui's own two hits: a `*`-prefixed
    # JSDoc body line, one of which documents apiUrl itself.
    body = '/**\n * `apiUrl("/api/items")` -> "/apps/u/writer/api/items"\n */\nexport const x = 1;\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


def test_ui107_severity_is_error(tmp_path: Path) -> None:
    # Arrange
    # error is only defensible because the measured population was
    # 12 literals across 3 repos. A noisier rule would have to be a warning.
    (tmp_path / "client.ts").write_text('fetch("/api/x");\n')
    # Act
    sev = [v.rule.severity for v in scan_path(tmp_path) if v.rule.id == "STX-UI107"]
    # Assert
    assert sev == ["error"]


def test_ui107_reports_the_offending_line_number(tmp_path: Path) -> None:
    # Arrange
    # the rule scans per-line precisely so the exemptions are
    # meaningful; that must also give an exact location, not a file-level nag.
    (tmp_path / "client.ts").write_text('const a = 1;\nconst b = 2;\nfetch("/api/x");\n')
    # Act
    lines = [v.line for v in scan_path(tmp_path) if v.rule.id == "STX-UI107"]
    # Assert
    assert lines == [3]


def test_ui107_does_not_flag_a_relative_path(tmp_path: Path) -> None:
    # Arrange
    # a relative path already survives being mounted anywhere, so
    # flagging it would be advice with no defect behind it.
    body = 'await fetch("api/items");\n'
    # Act
    fired = _ui107(tmp_path, "client.ts", body)
    # Assert
    assert "STX-UI107" not in fired


# --------------------------------------------------------------------------- #
# UI-108 — leaf-local <header> instead of the shared AppHeader primitive      #
# --------------------------------------------------------------------------- #


def test_ui108_flags_literal_header_element(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "page.html").write_text("<header class=\"app-head\">\n<h1>Hi</h1>\n</header>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    ids = [v.rule.id for v in violations]
    assert "STX-UI108" in ids


def test_ui108_skips_data_stx_app_header_mount(tmp_path: Path) -> None:
    # Arrange
    # the primitive mount is a div, not a header: the recommended
    # fix must not trip the rule that recommends it.
    (tmp_path / "page.html").write_text('<div data-stx-app-header data-app-title="X"></div>\n')

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI108" for v in violations)


# --------------------------------------------------------------------------- #
# UI-109 — hub duplicate builtin manifest vs the leaf's own manifest         #
# --------------------------------------------------------------------------- #


def test_ui109_flags_label_drift_between_hub_copy_and_leaf(tmp_path: Path, monkeypatch) -> None:
    # Arrange
    # hub copy says "Writer", the installed dist's leaf says
    # "SciTeX Writer": the writer fork, reproduced in miniature. The dist
    # lookup is pointed at a fake install root via the metadata path.
    import json

    hub = {
        "name": "writer_app",
        "label": "Writer",
        "icon": "fas fa-pen",
        "pip_package": "scitex-writer",
    }
    leaf = {
        "name": "writer_app",
        "label": "SciTeX Writer",
        "icon": "fas fa-file-alt",
        "pip_package": "scitex-writer",
    }
    target = tmp_path / "apps" / "workspace" / "writer_app"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(json.dumps(hub))

    import scitex_sdk.ui._linter._checker as checker

    monkeypatch.setattr(
        checker, "_leaf_manifest_from_dist", lambda pip: leaf if pip == "scitex-writer" else None
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    hits = [v for v in violations if v.rule.id == "STX-UI109"]
    assert len(hits) == 1
    assert "label" in hits[0].source_line


def test_ui109_stays_silent_when_leaf_dist_is_not_installed(tmp_path: Path) -> None:
    # Arrange
    # unresolvable leaf is not evidence of drift.
    import json

    target = tmp_path / "apps" / "workspace" / "ghost_app"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(
        json.dumps({"name": "ghost", "label": "Ghost", "icon": "fas fa-ghost", "pip_package": "scitex-ghost"})
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI109" for v in violations)


def test_ui109_ignores_name_only_difference(tmp_path: Path, monkeypatch) -> None:
    # Arrange
    # hub `name` is module identity, leaf `name` package identity:
    # they differ by design (writer module vs writer_app leaf), so a
    # name-only difference with matching label/icon is not drift.
    import json

    target = tmp_path / "apps" / "workspace" / "writer_app"
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(
        json.dumps({"name": "writer", "label": "SciTeX Writer", "icon": "fas fa-file-alt", "pip_package": "scitex-writer"})
    )

    import scitex_sdk.ui._linter._checker as checker

    leaf = {"name": "writer_app", "label": "SciTeX Writer", "icon": "fas fa-file-alt", "pip_package": "scitex-writer"}
    monkeypatch.setattr(
        checker, "_leaf_manifest_from_dist", lambda pip: leaf if pip == "scitex-writer" else None
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI109" for v in violations)


# --------------------------------------------------------------------------- #
# UI-110 — hardcoded icon in hub launcher JSON                                #
# --------------------------------------------------------------------------- #


def test_ui110_flags_hardcoded_icon_in_launcher_json(tmp_path: Path) -> None:
    # Arrange
    d = tmp_path / "apps" / "workspace" / "apps_app" / "launcher_links"
    d.mkdir(parents=True)
    (d / "create-app.json").write_text('{"name": "create-app", "icon": "fas fa-plus"}\n')

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI110" for v in violations)


def test_ui110_ignores_icon_keys_outside_launcher_links(tmp_path: Path) -> None:
    # Arrange
    # a leaf manifest's own icon is the source of truth, not drift.
    (tmp_path / "manifest.json").write_text('{"name": "x_app", "icon": "fas fa-x"}\n')

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI110" for v in violations)


def test_ui110_skips_declared_hub_native_tiles(tmp_path: Path) -> None:
    # Arrange
    # chat/settings have no leaf manifest; the explicit
    # "hub_native": true declaration keeps that auditable, not silent.
    d = tmp_path / "apps" / "workspace" / "apps_app" / "launcher_links"
    d.mkdir(parents=True)
    (d / "chat.json").write_text('{"name": "chat", "icon": "fas fa-comment", "hub_native": true}\n')

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI110" for v in violations)


# --------------------------------------------------------------------------- #
# UI-111 — unconditional !important layout override beating @media            #
# --------------------------------------------------------------------------- #


def test_ui111_flags_top_level_important_flex_direction_with_media_block(tmp_path: Path) -> None:
    # Arrange
    # the writer fork shape: unconditional directional override
    # plus a media query it silently beats.
    css = tmp_path / "app.css"
    css.write_text(
        ".pane { display: flex; }\n"
        ".pane-row { flex-direction: row !important; }\n"
        "@media (max-width: 600px) {\n"
        "  .pane-row { flex-direction: column; }\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    hits = [v for v in violations if v.rule.id == "STX-UI111"]
    assert len(hits) == 1


def test_ui111_flagged_line_is_the_unconditional_override(tmp_path: Path) -> None:
    # Arrange
    # the writer fork shape: unconditional directional override
    # plus a media query it silently beats.
    css = tmp_path / "app.css"
    css.write_text(
        ".pane { display: flex; }\n"
        ".pane-row { flex-direction: row !important; }\n"
        "@media (max-width: 600px) {\n"
        "  .pane-row { flex-direction: column; }\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert [v.line for v in violations if v.rule.id == "STX-UI111"] == [2]


def test_ui111_ignores_display_toggles(tmp_path: Path) -> None:
    # Arrange
    # tab-visibility state is JS-driven, not layout direction:
    # flagging it would push state into media queries where it belongs.
    css = tmp_path / "app.css"
    css.write_text(
        ".tab { display: none !important; }\n"
        ".tab.active { display: block !important; }\n"
        "@media (max-width: 600px) {\n"
        "  .tab { font-size: 12px; }\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI111" for v in violations)


def test_ui111_skips_important_scoped_inside_media(tmp_path: Path) -> None:
    # Arrange
    # legitimate breakpoint scoping is never the fork.
    css = tmp_path / "app.css"
    css.write_text(
        "@media (max-width: 600px) {\n"
        "  .pane { display: flex !important; }\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI111" for v in violations)


def test_ui111_skips_important_without_any_media_block(tmp_path: Path) -> None:
    # Arrange
    # no @media anywhere: nothing to fork, nothing to flag.
    css = tmp_path / "app.css"
    css.write_text(".pane { display: none !important; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI111" for v in violations)


def test_ui111_suppressed_when_running_inside_scitex_ui_itself(tmp_path: Path) -> None:
    # Arrange
    # the shell legitimately uses !important (mobile.css); the
    # rule fires on consumers, not on the SDK's own tree.
    css = tmp_path / "app.css"
    css.write_text(
        ".pane-row { flex-direction: row !important; }\n"
        "@media (max-width: 600px) {\n"
        "  .pane-row { flex-direction: column; }\n"
        "}\n"
    )

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=False)

    # Assert
    assert all(v.rule.id != "STX-UI111" for v in violations)

# --------------------------------------------------------------------------- #
# UI-112 — hardcoded <title> instead of shared {{ app_label }}                #
# --------------------------------------------------------------------------- #


def test_ui112_flags_hardcoded_title(tmp_path: Path) -> None:
    # Arrange
    # the cards drift: a literal tab title instead of the tile name.
    (tmp_path / "page.html").write_text("<html><head><title>SciTeX Card Board</title></head></html>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    hits = [v for v in violations if v.rule.id == "STX-UI112"]
    assert len(hits) == 1


def test_ui112_flagged_line_is_the_hardcoded_title(tmp_path: Path) -> None:
    # Arrange
    # the cards drift: a literal tab title instead of the tile name.
    (tmp_path / "page.html").write_text("<html><head><title>SciTeX Card Board</title></head></html>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert [v.line for v in violations if v.rule.id == "STX-UI112"] == [1]


def test_ui112_skips_template_variable_title(tmp_path: Path) -> None:
    # Arrange
    # dynamic by construction: the shared shell pattern.
    (tmp_path / "page.html").write_text("<title>{{ app_label }}</title>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI112" for v in violations)


# --------------------------------------------------------------------------- #
# UI-113 — consumer restyle of the shared AppHeader row                       #
# --------------------------------------------------------------------------- #


def test_ui113_flags_leaf_app_header_override(tmp_path: Path) -> None:
    # Arrange
    # row height/placement/font-size must come from the SDK alone.
    css = tmp_path / "app.css"
    css.write_text(".stx-app-header { height: 64px; }\n.stx-app-header__title { font-size: 20px; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    hits = [v for v in violations if v.rule.id == "STX-UI113"]
    assert len(hits) == 2


def test_ui113_skips_unrelated_selectors(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "app.css"
    css.write_text(".stx-app-body { padding: 8px; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI113" for v in violations)


def test_ui113_suppressed_when_running_inside_scitex_ui_itself(tmp_path: Path) -> None:
    # Arrange
    # the SDK defines that row; the rule fires on consumers.
    css = tmp_path / "app.css"
    css.write_text(".stx-app-header { height: 64px; }\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=False)

    # Assert
    assert all(v.rule.id != "STX-UI113" for v in violations)


def test_ui108_skips_sdk_pane_headers(tmp_path: Path) -> None:
    # Arrange
    # stats-pattern pane headers follow the SDK panes contract.
    (tmp_path / "page.html").write_text(
        '{% scitex_panes "stats" %}<header class="stats-pane__header" data-stx-pane-header>\n<h2>X</h2>\n</header>\n'
    )

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI108" for v in violations)


def test_ui113_ignores_commented_out_overrides(tmp_path: Path) -> None:
    # Arrange
    # commented code is not a restyle.
    css = tmp_path / "app.css"
    css.write_text("/* .stx-app-header { height: 64px; }\n   override parked. */\n.app { color: red; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI113" for v in violations)


def test_ui108_skips_django_hash_comment_mention(tmp_path: Path) -> None:
    # Arrange
    # a {# ... #} explanation of the no-local-header rule.
    (tmp_path / "page.html").write_text("{# it is a div, never a <header>. #}\n<div>x</div>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI108" for v in violations)


# --------------------------------------------------------------------------- #
# UI-114 — leaf-local button base instead of shared .stx-button               #
# --------------------------------------------------------------------------- #


def test_ui114_flags_parallel_btn_base(tmp_path: Path) -> None:
    # Arrange
    # the writer fork: a full parallel button system.
    css = tmp_path / "app.css"
    css.write_text(".btn {\n  display: inline-flex;\n  padding: 4px 12px;\n}\n.btn-primary { background: blue; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    # the base fires once; variants keyed off it do not multiply it.
    hits = [v for v in violations if v.rule.id == "STX-UI114"]
    assert len(hits) == 1


def test_ui114_parallel_btn_base_fires_on_the_first_line(tmp_path: Path) -> None:
    # Arrange
    # the writer fork: a full parallel button system.
    css = tmp_path / "app.css"
    css.write_text(".btn {\n  display: inline-flex;\n  padding: 4px 12px;\n}\n.btn-primary { background: blue; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert [v.line for v in violations if v.rule.id == "STX-UI114"] == [1]


def test_ui114_flags_bare_button_element_rule(tmp_path: Path) -> None:
    # Arrange
    css = tmp_path / "app.css"
    css.write_text("button {\n  font-size: 13px;\n}\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI114" for v in violations)


def test_ui114_ignores_stx_button_usage(tmp_path: Path) -> None:
    # Arrange
    # adopting the primitive is the fix, never the violation.
    css = tmp_path / "app.css"
    css.write_text(".my-pane .stx-button { margin-left: 8px; }\n.stx-button--primary { font-weight: 600; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI114" for v in violations)


def test_ui114_suppressed_when_running_inside_scitex_ui_itself(tmp_path: Path) -> None:
    # Arrange
    # the SDK defines the primitive; the rule fires on consumers.
    css = tmp_path / "app.css"
    css.write_text(".btn {\n  display: inline-flex;\n}\n")

    # Act
    violations = scan_path(tmp_path, treat_as_consumer=False)

    # Assert
    assert all(v.rule.id != "STX-UI114" for v in violations)


def test_ui102_skips_content_color_files(tmp_path: Path) -> None:
    # Arrange
    # annotation palettes are content, not UI chrome.
    css = tmp_path / "annotations.css"
    css.write_text(".ann-red { color: #ef4444; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI102" for v in violations)


def test_ui102_still_flags_ui_chrome_hex(tmp_path: Path) -> None:
    # Arrange
    # the exemption is path-based, not a free pass.
    css = tmp_path / "editor.css"
    css.write_text(".pane { background: #1b1b29; }\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI102" for v in violations)


def test_ui112_flags_multiline_hash_comment(tmp_path: Path) -> None:
    # Arrange
    # Django strips only single-line {# #}; a multi-line block
    # is emitted VERBATIM (measured twice 2026-10-22: journal app.html,
    # scholar workspace_assets).
    (tmp_path / "page.html").write_text("{# Shared header.\nSpans two lines. #}\n<p>x</p>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert any(v.rule.id == "STX-UI112" for v in violations)


def test_ui112_ignores_single_line_hash_comment(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "page.html").write_text("{# one-liner #}\n<p>x</p>\n")

    # Act
    violations = scan_path(tmp_path)

    # Assert
    assert all(v.rule.id != "STX-UI112" for v in violations)
