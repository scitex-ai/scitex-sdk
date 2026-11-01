# Install SDK App contract

The implementation belongs to `scitex-sdk`, imported through
`scitex_sdk.app`. App/UI component identifiers do not name separate
installation requirements.

The 0.3.0 consolidation is published (all releases through 0.3.12
verified live on PyPI). For Django GUI development, run
`pip install 'scitex-sdk[gui]'`; add `chat`, `mcp` or `cli` when
required. From a reviewed checkout, `pip install -e '.[gui]'` works too.
The `project`/`all` extras require Dev>=0.62 (public) — normal
resolution succeeds. Contributor tools use
`pip install -e . --group dev`, with pip>=25.1.

Read the SDK workflow skill, then verify the installed package and current
source. Use `import scitex_sdk.app` and `scitex-sdk app --help`.
