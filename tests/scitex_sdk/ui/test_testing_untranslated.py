#!/usr/bin/env python3
"""scitex_sdk.ui.testing.find_untranslated / assert_no_untranslated."""

from scitex_sdk.ui.testing import assert_no_untranslated, find_untranslated


def test_find_untranslated_reports_an_english_text_node():
    # Arrange
    html = "<button>Save</button><p>保存</p>"
    # Act
    leftovers = find_untranslated(html, ["Save"])
    # Assert
    assert leftovers == ["Save"]


def test_find_untranslated_reports_an_english_title_attribute():
    # Arrange
    html = '<button title="Undo">↶</button>'
    # Act
    leftovers = find_untranslated(html, ["Undo"])
    # Assert
    assert leftovers == ["Undo"]


def test_find_untranslated_ignores_a_partial_word_match():
    # Arrange
    html = "<span>Saved</span>"
    # Act
    leftovers = find_untranslated(html, ["Save"])
    # Assert
    assert leftovers == []


def test_find_untranslated_ignores_msgids_inside_a_json_script_catalog():
    # Arrange
    html = '<script type="application/json">{"Save": "保存"}</script><b>保存</b>'
    # Act
    leftovers = find_untranslated(html, ['{"Save": "保存"}'])
    # Assert
    assert leftovers == []


def test_find_untranslated_normalises_whitespace():
    # Arrange
    html = "<label>\n  Export\n  figure </label>"
    # Act
    leftovers = find_untranslated(html, ["Export figure"])
    # Assert
    assert leftovers == ["Export figure"]


def test_find_untranslated_refuses_an_empty_render():
    # Arrange
    html = "  "
    # Act
    error = _raised(lambda: find_untranslated(html, ["Save"]))
    # Assert
    assert isinstance(error, ValueError)


def test_assert_no_untranslated_names_the_leftover_string():
    # Arrange
    html = "<h1>Gallery</h1>"
    # Act
    error = _raised(lambda: assert_no_untranslated(html, ["Gallery"]))
    # Assert
    assert "'Gallery'" in str(error)


def _raised(action):
    try:
        action()
    except (AssertionError, ValueError) as error:
        return error
    return None
