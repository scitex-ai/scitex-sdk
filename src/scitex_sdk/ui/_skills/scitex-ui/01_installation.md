# Install SDK UI components

The implementation belongs to `scitex-sdk`, imported through
`scitex_sdk.ui`. App/UI component identifiers do not name separate
installation requirements.

The 0.3.0 consolidation candidate is not published yet. From its reviewed
checkout, run `pip install -e '.[gui]'` for Django GUI development; add
`chat`, `mcp` or `cli` when required. After publication the equivalent install
is `pip install 'scitex-sdk[gui]'`.
The `project`/`all` extra requires published Dev>=0.62.0 and is a genuine
release gate while that API is unavailable. Contributor tools use
`pip install -e . --group dev`, with pip>=25.1.

Read the SDK workflow skill, then verify the installed package and current
source. Use `import scitex_sdk.ui` and `scitex-sdk ui --help`.
