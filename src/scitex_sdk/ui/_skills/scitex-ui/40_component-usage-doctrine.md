---
description: |
  [TOPIC] SDK UI component usage and header enforcement
  [DETAILS] The actual UI-101 through UI-116 source checks, mandatory SDK header ownership, native hook installation, and coverage limits.
tags: [scitex-ui-component-usage-doctrine, lint]
---

# SDK UI component usage

Use SDK components and shared CSS for application chrome. Pass app labels,
versions, and scope availability through component options. Scientific figures,
annotations, and data palettes remain content, not application chrome.

Component examples are in `32_frontend-components.md`; theme guidance is in
`34_frontend-components-theme.md`. The implementation is
`scitex_sdk.ui._linter._rules` and `_checker`, with header ownership in
`_header_contract`.

## Source checks

The installed corpus contains **16** rules. IDs use the `STX-` prefix.
Severity below is the current `build_rules()` output, not a future migration
promise. `scitex-sdk ui lint PATH` returns nonzero for any finding, including
warnings.

| ID | Current severity | Detection and remedy |
| --- | --- | --- |
| UI-101 | warning | Native `select` without `data-app-themed` opt-in. Use the SDK Dropdown or an explicitly themed native control. |
| UI-102 | warning | Raw hex/rgb/rgba in UI CSS. Use shared tokens; recognized content-palette paths are exempt from this colour check. |
| UI-103 | warning | Copied shell/primitive selector signatures in consumer static CSS. Import SDK styles instead of maintaining copies. |
| UI-104 | warning | Consumer edits under shared shell/primitives paths. Request SDK-owned changes; the currently shipped rule is still warning tier. |
| UI-105 | warning | Raw colour inside scrollbar rules. Import the shared scrollbar surface; local token indirection alone does not satisfy UI-115. |
| UI-106 | warning | Native select with more than eight options without filtering/Combobox enhancement or its explicit opt-out. |
| UI-107 | error | Literal root-anchored `/api/` or `/apps/` client request paths. Use the host-provided mounted API base. |
| UI-108 | warning | Literal local `header` markup, except pane headers and supported comment exclusions. Mount the SDK AppHeader instead. |
| UI-109 | warning | Duplicate host builtin manifest label/icon disagrees with the leaf manifest. Keep identity leaf-owned. |
| UI-110 | warning | Hardcoded icon in host launcher JSON. Render the leaf manifest icon. |
| UI-111 | warning | Unconditional `!important` direction/wrap declaration in a responsive stylesheet. Let media rules control the layout. |
| UI-112 | warning | Hardcoded Django tab title or unrenderable multiline `{# ... #}` comment. Use shared title context and `{% comment %}` blocks. |
| UI-113 | warning | Shared header/dropdown ownership violations. The same detector also drives the mandatory project rule below. |
| UI-114 | warning | Parallel leaf button base. Use `.stx-button` and its variants; scope content-specific rules to content controls. |
| UI-115 | warning | Local scrollbar colouring or an unthemed scroll container. Import `shell/scrollbars.css`, also included by the shell bundle. |
| UI-116 | warning | Literal `SciTeX `-prefixed `data-app-title` or Django title. Use the short app label on those surfaces. |

The `scitex_dev.linter.plugins` entry point catalogs these rules. Its generic
checker is Python-AST-only; its empty frontend `checkers` slot does **not**
execute CSS/HTML scanning. The standalone SDK lint command executes the walker.

## Mandatory header and dropdown ownership

`scitex_sdk._audit_plugin:get_plugin` registers `PS-SDK-HEADER` through
`scitex_dev.audit.project`. The normal Dev project auditor executes it at error
severity, independently of the warning classification of UI-113.

The SDK renderer owns header markup, typography, geometry, and project
selector children. Consumer code may use an empty `data-stx-app-header` mount,
the SDK React binding, and the SDK ProjectPicker mount/template tag. Copying
canonical class names onto handwritten header, trigger, option, or search
markup does not grant ownership. Disabled scope choices must remain visible.

The shared detector rejects:

- Direct consumer CSS for SDK header/dropdown selectors and inline styles on
  those elements.
- Recognizable local app-header markup and handwritten canonical header or
  project-selector child markup.
- A generic ancestor button rule that demonstrably reaches a literal shared
  header and overrides its appearance. Independent toolbar controls are allowed.

Only the two exact canonical SDK CSS resources in a project named `scitex-sdk`
own these selectors. A whole SDK repository is not exempt. Consumers may use
visibility-only rules on explicitly leaf-owned slot content; this preserves
static-export fallback lifecycle without granting control over SDK typography.

## Native agent bindings

The SDK retains its scrollbar warning and declares two header guards:
`sdk.header-contract` before native edits and
`sdk.header-contract-after-shell` after shell/apply-patch changes. All accept
native payload dictionaries and return violation strings. Dev 0.62.6 contains
the canonical execution/installation bridge; the SDK `cli` and `project`
extras require that floor.

```bash
scitex-dev hooks install --provider scitex-sdk --config .claude/settings.json --harness claude --dry-run
```

Remove `--dry-run` to merge bindings, preserving unrelated settings and hooks.
Use the intended target interpreter; its installed entry-point metadata must
include the SDK provider. Discovery/listing alone does not activate interception.
Verify a prohibited native tool call before claiming that a running client
loaded the configuration. A pre-edit refusal prevents that edit; a post-tool
finding reports a completed change and does not roll back files.

Hermes additionally requires its native configuration writer, command consent,
and startup or supported plugin/config reload. Do not fabricate allowlist
approvals. Only `pre_tool_call` can veto; `post_tool_call` is an observer.
Project auditing, CI, and correctly installed pre-push gates remain independent
of native client support.

## Scope and limits

Editor hooks resolve the actual target repository even when client cwd is
HOME. Repository context uses tracked and nonignored Git inputs, avoiding
ignored data/media/cache trees. Explicit editor targets are still checked when
ignored. Post-shell checks inspect staged, unstaged, and untracked files,
including unborn repositories. Shell calls outside a repository have no claimed
project-source scope and are not refused as failed header inspections.

Tests, examples, documentation artifacts, and build directories are excluded.
Vite-declared CSS output is excluded only when authored frontend inputs are
present: imported canonical SDK CSS is not a consumer fork. Missing scanner
imports and unreadable claimed source fail verification.

This is literal-source analysis, not a computed-style proof. Dynamic DOM/style
generation, complex selector cascades, and browser inheritance require the real
SDK browser contract suite (`npm run test:headers`) and host integration checks.
Keep component behavior and visual contracts in SDK-owned tests; fix consumers
rather than adding per-app typography or geometry overrides.
