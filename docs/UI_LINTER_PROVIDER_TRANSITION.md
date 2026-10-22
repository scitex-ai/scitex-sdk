# UI linter provider transition

The SDK owns the UI implementation and publishes its seven existing rules as
`scitex_dev.linter.plugins` entry point `ui`, targeting
`scitex_sdk.ui._linter_plugin:get_plugin`. A transitive dependency can still
install `scitex-ui`, whose entry point exports the same rule IDs with older
metadata. Registering both providers would make ownership ambiguous.

The SDK's provider payload retains its four historical keys and adds
`replaces`, a tuple containing the public
`scitex_dev.linter.spi.ProviderReplacement` contract. This declaration matches
only distribution `scitex-ui`, entry-point name `ui`, and target
`scitex_ui._linter_plugin:get_plugin`, with the complete rule IDs
`STX-UI101` through `STX-UI107` (the predecessor's corpus; the drift pack
UI-108+ is additive SDK surface, not replacement scope). A compatible Dev
checks installed distribution identity and both complete rule corpora before
selecting the SDK. Entry-point iteration order cannot choose the owner. The
loader records the transition in `provider_replacements`; malformed, partial,
ambiguous, or unrelated duplicate ownership still fails.

This transition preserves the rule IDs and the old UI distribution's APIs.
It does not uninstall, modify, or import old UI as an SDK runtime dependency.
The legacy UI standalone walker remains available to its existing callers.
SDK non-Python UI checks still run through `scitex-sdk ui lint`; entry-point
registration makes the corpus discoverable without adding Python AST checkers.

The replacement SPI is imported only when `get_plugin()` is called. Importing
the SDK, importing its provider module, and using the standalone UI walker do
not acquire a new Dev dependency. Activating the provider with an older Dev
fails with an actionable compatibility error instead of dropping its
declaration. The optional `cli` and `project` extras and contributor `dev` group
therefore require `scitex-dev>=0.62` (Dev 0.62.4 with the SPI is public); `all`
includes both extras. The
project primitive itself existed in Dev 0.62.0, but installing an older Dev for
that API would also discover the SDK's incompatible linter provider. Every
SDK tooling installation consequently selects the compatible engine.

# Gate narrative, completed — read as history, not a pending gate

SDK 0.3.3 first declared the replacement of the exact legacy UI linter
provider (seven rules UI-101..107, current corpus UI-101..114 per
`src/scitex_sdk/ui/_linter/_rules.py`). It shipped on PyPI alongside all
releases through 0.3.12 (verified live). The compatible Dev
(`scitex-dev>=0.62.4`, public) carries the `ProviderReplacement` SPI, so
both distributions may remain installed while Dev registers the rules —
ownership resolves to the SDK, recorded in `provider_replacements`.
Standalone SDK UI use keeps Dev optional. `pip check` against published
dependencies and the normal built-wheel `[all]` install gate ran green
for each release; see CI history. Consumer migration and strict published
dependency retirement remain separate tracked gates (see
[the release sequence](RELEASE_BOOTSTRAP.md)).
