---
name: scitex-sdk
description: |
  [WHAT] Orchestrator skill for the SciTeX SDK — routes App scaffolding/validation, UI shell primitives, and SDK release gates to the scitex-app / scitex-ui component skills.
  [WHEN] Use when the user asks to "scaffold a SciTeX app", "validate my app manifest", "mount the shared AppHeader", "lint UI drift", "cut an SDK release", or mentions the top-level `scitex-sdk` CLI/API.
  [HOW] `pip install 'scitex-sdk[gui,cli]'`, verify with `scitex-sdk --help` and `import scitex_sdk.app`; then follow 01..04 below, delegating component detail to the scitex-app / scitex-ui skills.
tags: [scitex-sdk]
---

# SciTeX SDK workflow

- [Install](01_installation.md) — extras, verification commands.
- [Quick start](02_quick-start.md) — scaffold, wizard, validate in 5 min.
- [Python API map](03_python-api.md) — the three lazy facades.
- [CLI reference](04_cli-reference.md) — top-level command tree.

1. Read `../../_docs/APP_DEVELOPER_GUIDE.md` and the relevant App/UI component
   skill under `../../app/_skills/scitex-app/` or `../../ui/_skills/scitex-ui/`.
2. Pin the actual source revisions and inspect runtime behavior. Documentation
   is a guide; reconcile stale claims with current code and observed behavior.
3. Keep domain GUI code in the leaf's `_django` package. Import App/UI from
   `scitex_sdk`; let Hub provide authenticated capabilities and generic mounts.
4. Preserve existing data identities, permission refusal behavior, CSRF and
   project confinement. Never use another user's data as a test fixture.
5. Verify an installed wheel as well as source, including template/static/npm
   exports, standalone and plugin modes, and UI interactions for desktop/mobile.
6. Complete tests and reviewable packaging before release or cutover. Do not
   archive an old owner while active consumers still require it.

Use CLI/MCP commands after applying this workflow. Skill-first means read the
workflow first; it does not forbid execution tools.
