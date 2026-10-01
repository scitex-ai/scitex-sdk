---
name: scitex-sdk
description: Build or migrate a SciTeX leaf GUI using the shared SDK, with standalone and Hub plugin validation.
---

# SciTeX SDK workflow

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
