#!/usr/bin/env python3
"""The shipped class manifest must equal what the TypeScript source declares.

WHY THIS EXISTS, and it is not for this package's own benefit.

A consumer that lints CSS against scitex-ui's shell needs to know which classes
this package RENDERS. That fact is not recoverable from the string:

    .stx-shell-sidebar__header          a real shell element   -> their rule fires
    .stx-shell-sidebar__header-compact  a consumer's own class -> it must not

No grammar separates those two. The difference is whether WE render it, which is
a fact about this tree and nowhere else. Before this manifest existed, the only
way for a consumer to know was to copy a list by hand across a package
boundary — and then NOTHING HERE FAILED when we added an element. Their table
went stale silently, which is detection loss by construction: the rule still
runs, still passes, and simply sees less.

THIS GUARD IS THE WHOLE POINT, not the JSON. Shipping a manifest without it
would be a hand-maintained list with extra steps. With it, adding a component or
an element and forgetting to regenerate is OUR red, here, in our own suite —
the staleness moves from their invisible gap to our visible failure.

A NATIVE CLIENT NEEDS THE SAME DATA FOR A STRONGER REASON. iOS and Android
cannot read a stylesheet at all, so this vocabulary either exists as data or it
does not exist for them. That upgrades the manifest from a courtesy to a
consumer into this package's own interface.

WHAT IT DELIBERATELY DOES NOT ENUMERATE:

    MODIFIERS are listed but are NOT the contract. A consumer should match them
    by GRAMMAR — ``<entry>(?:--[\\w-]+)?`` — because modifiers are open-ended
    state. They appear here so a consumer can write fixtures, not so they can
    build a table that goes stale on the next state we add.

    CALLER-SUPPLIED classes cannot be enumerated at all. Several call sites add
    whatever a caller passes. The manifest therefore declares itself a LOWER
    BOUND *in its own payload* — a manifest presented as complete is a gate that
    cannot fail wearing a list.
"""

from __future__ import annotations

import json
import re

from tests._checkout import package_dir

_TS_DIR = package_dir() / "static" / "scitex_sdk" / "ui" / "ts"
_MANIFEST = package_dir() / "static" / "scitex_sdk" / "ui" / "class-manifest.json"

#: The de-facto registry: every component module declares its own base name.
_CLS = re.compile(r'^\s*const\s+CLS\s*=\s*"([^"]+)"', re.M)

#: A class built from that base, e.g. `${CLS}__item--active`.
_BUILT = re.compile(r"`\$\{CLS\}([^`]*)`")

#: Split a suffix into its element half and its modifier half. BEM order is
#: block__element--modifier, so the element runs up to the first `--`.
_ELEMENT = re.compile(r"(__[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*?)(?=--|$)")
_MODIFIER = re.compile(r"(--[A-Za-z0-9_-]+)$")

#: A class name that comes from the CALLER, so no static reading can name it.
_CALLER_SUPPLIED = re.compile(
    r"classList\.add\(\s*(className|config\.className|item\.cssClass)\s*\)"
)


def _ts_files():
    return sorted(_TS_DIR.rglob("*.ts"))


def build_manifest() -> dict:
    """Derive the manifest from source. This is the generator AND the oracle.

    Deriving both from one function is deliberate: the committed JSON is
    compared against THIS, so a drift is a difference between the file and the
    tree rather than between two hand-written lists.
    """
    components: dict[str, dict[str, list[str]]] = {}
    unenumerable: list[str] = []

    for path in _ts_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(_TS_DIR).as_posix()

        for line_no, line in enumerate(text.splitlines(), start=1):
            if _CALLER_SUPPLIED.search(line):
                unenumerable.append(f"{rel}:{line_no}")

        found = _CLS.search(text)
        if not found:
            continue
        base = found.group(1)
        entry = components.setdefault(base, {"elements": set(), "modifiers": set()})
        for suffix in _BUILT.findall(text):
            element = _ELEMENT.match(suffix)
            if element and element.group(1):
                entry["elements"].add(element.group(1))
            modifier = _MODIFIER.search(suffix)
            if modifier:
                entry["modifiers"].add(modifier.group(1))

    return {
        "schema_version": 1,
        "completeness": "LOWER_BOUND",
        "completeness_reason": (
            "Class names added from caller-supplied values cannot be derived "
            "statically. Treat this manifest as a lower bound: everything listed "
            "IS rendered by scitex-ui, but scitex-ui may render names not listed."
        ),
        "unenumerable_sites": sorted(unenumerable),
        "modifiers_are_not_a_contract": (
            "Modifiers are listed for fixtures only. Match them by grammar "
            "-- <entry>(?:--[\\w-]+)? -- because they are open-ended state."
        ),
        "generated_by": "tests/develop/test_class_manifest_matches_source.py",
        "components": {
            base: {
                "elements": sorted(v["elements"]),
                "modifiers": sorted(v["modifiers"]),
            }
            for base, v in sorted(components.items())
        },
    }


def _serialise(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, sort_keys=False) + "\n"


# --- the guard ------------------------------------------------------------


def test_the_source_scan_is_not_empty():
    # Arrange -- an empty scan would make every comparison below pass
    # vacuously, which is the failure this whole file exists to prevent.
    files = _ts_files()
    # Act
    count = len(files)
    # Assert
    assert count > 50, f"only {count} .ts files found under {_TS_DIR} -- wrong root?"


def test_the_manifest_declares_at_least_one_component():
    # Arrange
    manifest = build_manifest()
    # Act
    components = manifest["components"]
    # Assert
    assert len(components) > 5, (
        f"derived only {len(components)} components; the `const CLS` convention "
        f"may have changed, in which case this guard is measuring nothing"
    )


def test_the_shipped_manifest_matches_the_source():
    """THE GUARD. Adding an element without regenerating fails HERE."""
    # Arrange
    derived = build_manifest()
    # Act
    shipped = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    # Assert
    assert shipped == derived, (
        "class-manifest.json is out of date with the TypeScript source.\n\n"
        "This is the guard doing its job: a consumer's CSS rule reads this file, "
        "and a stale manifest makes their check silently narrower.\n\n"
        "Regenerate with:\n"
        "    python -c \"import json,sys; sys.path.insert(0,'tests');\"\n"
        "  or copy the derived value printed by pytest -vv on this test.\n\n"
        f"DERIVED:\n{_serialise(derived)}"
    )


def test_the_manifest_declares_itself_a_lower_bound():
    """A manifest presented as complete is a gate that cannot fail."""
    # Arrange
    shipped = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    # Act
    completeness = shipped.get("completeness")
    # Assert
    assert completeness == "LOWER_BOUND", (
        "the manifest must declare its own incompleteness in its payload, not "
        "only in documentation -- a consumer reads the file, not the docstring"
    )


def test_the_unenumerable_sites_are_named_not_merely_counted():
    # Arrange
    shipped = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    # Act
    sites = shipped.get("unenumerable_sites", [])
    # Assert
    assert sites, (
        "no caller-supplied call sites recorded. Either they were all removed "
        "-- in which case the manifest is now COMPLETE and this file should say "
        "so deliberately -- or the detector stopped matching. Both need a human."
    )


# --- controls on the extractor itself -------------------------------------


def test_cls_matches_a_real_declaration():
    # Arrange
    sample = '  const CLS = "stx-shell-sidebar";\n'
    # Act
    matched = _CLS.search(sample)
    # Assert
    assert matched is not None


def test_cls_ignores_a_mere_mention_of_the_name():
    """NEGATIVE control: prose ABOUT `const CLS` is not a declaration."""
    # Arrange
    sample = "// every component declares its own const CLS base name\n"
    # Act
    matched = _CLS.search(sample)
    # Assert
    assert matched is None


def test_built_matches_a_real_template_literal():
    # Arrange
    sample = "el.classList.add(`${CLS}__item--active`);"
    # Act
    matched = _BUILT.search(sample)
    # Assert
    assert matched is not None


def test_built_ignores_a_plain_string_class():
    """NEGATIVE control. A literal class is not built from CLS, so it is not
    part of this component's derived vocabulary and must not be collected."""
    # Arrange
    sample = 'el.classList.add("stx-shell-layout");'
    # Act
    matched = _BUILT.search(sample)
    # Assert
    assert matched is None


def test_element_matches_and_stops_before_the_modifier():
    """POSITIVE control, and the boundary is the whole point: reporting
    `__item--active` as an ELEMENT would push open-ended state into a
    consumer's table instead of leaving it to their grammar."""
    # Arrange
    sample = "__item--active"
    # Act
    matched = _ELEMENT.match(sample)
    # Assert
    assert matched.group(1) == "__item"


def test_element_ignores_a_bare_modifier():
    """NEGATIVE control: `${CLS}--collapsed` has NO element half."""
    # Arrange
    sample = "--collapsed"
    # Act
    matched = _ELEMENT.match(sample)
    # Assert
    assert matched is None or not matched.group(1)


def test_modifier_matches_a_trailing_modifier():
    # Arrange
    sample = "__item--active"
    # Act
    matched = _MODIFIER.search(sample)
    # Assert
    assert matched is not None


def test_modifier_ignores_an_element_with_a_hyphen():
    """NEGATIVE control, and it is the trap this pattern exists to avoid:
    `__new-input` is ONE element whose name contains a hyphen, not an element
    plus a `-input` modifier. A single-hyphen pattern would split it."""
    # Arrange
    sample = "__new-input"
    # Act
    matched = _MODIFIER.search(sample)
    # Assert
    assert matched is None


def test_the_caller_supplied_detector_matches_a_variable_add():
    # Arrange
    sample = "if (el) el.classList.add(className);"
    # Act
    matched = _CALLER_SUPPLIED.search(sample)
    # Assert
    assert matched is not None


def test_the_caller_supplied_detector_ignores_a_literal_add():
    """NEGATIVE control: a literal class IS enumerable, so it must not be
    counted as a reason the manifest is incomplete."""
    # Arrange
    sample = 'el.classList.add("stx-shell-layout");'
    # Act
    matched = _CALLER_SUPPLIED.search(sample)
    # Assert
    assert matched is None
