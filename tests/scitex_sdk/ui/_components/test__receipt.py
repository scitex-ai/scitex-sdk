#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._components._receipt."""

import re

import pytest

from scitex_sdk import ui as scitex_ui
from tests._checkout import package_dir
from scitex_sdk.ui._components._receipt import Receipt

_STATIC = package_dir() / "static"
_STATES = ("unknown", "sent", "seen", "failed")


class TestReceipt:
    def test_metadata_and_files(self, check_metadata):
        # Arrange
        # Act
        # Assert
        assert check_metadata(Receipt) is Receipt

    def test_ships_both_styling_and_behaviour(self):
        # Arrange
        # Act
        # Assert
        assert Receipt.ts_entry and Receipt.css_file, (
            "a receipt with CSS but no behaviour would leave every adopter "
            "writing the state machine themselves, which is what this replaces"
        )


class TestFourStatesSurviveInBothLayers:
    """`unknown` and `failed` are the whole point; losing either is the bug.

    A read/unread boolean cannot express "no signal yet", and collapsing that
    into either pole reports undelivered messages as delivered. scitex-cards
    asked for the failed state explicitly even though their first version will
    not set it. So both layers are checked: drop a state from the stylesheet and
    it renders unstyled; drop it from the module and it becomes unreachable.
    """

    def _css(self) -> str:
        return (_STATIC / Receipt.css_file).read_text()

    def _ts(self) -> str:
        root = _STATIC / "scitex_sdk/ui/ts/app/receipt"
        return "\n".join(p.read_text() for p in root.glob("*.ts"))

    @pytest.mark.parametrize("state", _STATES)
    def test_state_has_a_style(self, state):
        # Arrange
        css = self._css()
        # Act
        styled = f".stx-app-receipt--{state}" in css
        # Assert
        assert styled, (
            f"no .stx-app-receipt--{state} rule; the {state} state would render "
            f"indistinguishably from another and silently misreport delivery"
        )

    @pytest.mark.parametrize("state", _STATES)
    def test_state_is_declared_by_the_module(self, state):
        # Arrange
        ts = self._ts()
        # Act
        declared = f'"{state}"' in ts
        # Assert
        assert declared, f"the module no longer declares the {state} state"

    def test_unknown_is_the_default_state(self):
        # Arrange
        ts = self._ts()
        # Act
        # The default must be `unknown`: a receipt nobody updated must never
        # read as delivered.
        defaulted = re.search(r"config\.state\s*\?\?\s*\"unknown\"", ts) is not None
        # Assert
        assert defaulted, (
            "the starting state must default to 'unknown'; defaulting to 'sent' "
            "would claim a delivery that never happened"
        )

    def test_unrecognised_state_raises_rather_than_falling_back(self):
        # Arrange
        ts = self._ts()
        # Act
        throws = "throw new Error" in ts
        # Assert
        assert throws, (
            "an unrecognised state must fail loudly; silently rendering it as "
            "'unknown' would hide a delivery failure behind 'no signal yet'"
        )

    def test_guard_is_not_vacuous(self):
        # Arrange
        # Act
        rules = re.findall(r"\.stx-app-receipt--([a-z]+)", self._css())
        # Assert
        assert set(rules) == set(_STATES), (
            f"stylesheet defines {sorted(set(rules))}, expected {sorted(_STATES)} — "
            f"the extraction drifted, so the per-state checks prove nothing"
        )


class TestStylesheetReachesThePage:
    """0.11.1 shipped badge.css importable by nothing; do not repeat it here."""

    @pytest.mark.parametrize("bundle", ["app.css", "all.css"])
    def test_bundle_imports_the_stylesheet(self, bundle):
        # Arrange
        text = (_STATIC / "scitex_sdk/ui/css" / bundle).read_text()
        # Act
        imported = "./app/receipt.css" in text
        # Assert
        assert imported, (
            f"{bundle} does not import app/receipt.css; adopters would get the "
            f"class name and no styling. Regenerate: npx tsx css/_build-index.ts"
        )


# EOF
