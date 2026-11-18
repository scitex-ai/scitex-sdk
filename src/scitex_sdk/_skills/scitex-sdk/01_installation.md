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

The core App/UI facades and `scitex_sdk.ui.project_scope.ProjectEntry` remain
usable without Django. The creator, host/local helpers,
`ui.project_scope`, `ui.i18n` and namespace URL helpers use a shared `[gui]`
install hint when Django itself is missing, retaining the original cause.
Those guards preserve missing-peer and Django configuration errors. Chat
adapters use separate guards and require independent dependency validation.
Host settings and capabilities are configured separately.

Verify the install and the current source:

- `scitex-sdk --help` lists `app`, `gui`, `ui`, `docs`, `skills`, `mcp`,
  `list-python-apis` plus shell completion.
- `python -c "import scitex_sdk.app, scitex_sdk.ui"` imports both facades.

Component detail lives in the scitex-app / scitex-ui skills; this skill
only routes. Read the SDK workflow (SKILL.md) first.
