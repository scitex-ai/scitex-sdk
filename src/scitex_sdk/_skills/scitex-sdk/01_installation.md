---
description: [extras, verification commands for the SDK install] See SKILL.md workflow; component detail in scitex-app / scitex-ui skills.
tags: [scitex-sdk]
---

# Install the SciTeX SDK

The implementation belongs to `scitex-sdk`, imported through
`scitex_sdk.app` (App contract), `scitex_sdk.ui` (UI shell), and
`scitex_sdk.project` (project primitive).

For SDK CLI + Django GUI development, run
`pip install 'scitex-sdk[gui,cli]'`; add `chat` or `mcp` when required.
`project`/`all` extras require Dev>=0.62 (public) — normal resolution
succeeds. From a reviewed checkout, `pip install -e '.[gui,cli]'` works too.
Contributor tools use `pip install -e . --group dev`, with pip>=25.1.

Verify the install and the current source:

- `scitex-sdk --help` lists `app`, `gui`, `ui`, `docs`, `skills`, `mcp`,
  `list-python-apis` plus shell completion.
- `python -c "import scitex_sdk.app, scitex_sdk.ui"` imports both facades.

Component detail lives in the scitex-app / scitex-ui skills; this skill
only routes. Read the SDK workflow (SKILL.md) first.
