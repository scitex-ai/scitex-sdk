---
description: Source-only SDK Web API descriptor checks dispatched by scitex-dev.
tags: [web-api, contracts, auditing, hooks]
---

# Web API contract enforcement

Register a descriptor **data object**, not a provider function:

```toml
[project.entry-points."scitex.apis"]
my_api = "my_package.api:PLUGIN"
```

`PLUGIN` must be an SDK `ApiPlugin` whose id equals `my_api`. Declare its
`ApiRoute`, schemas, authentication/scope, rate and idempotency contracts using
constructors from `scitex_sdk.app.api_plugin`. Handler strings name owned
functions or class methods, such as `my_package.views:read_item`.

The SDK's `PS-SDK-WEB` rule is registered through the existing
`scitex_dev.audit.project` provider. Dev's project audit dispatches it alongside
other installed leaf rules. For example:

```bash
scitex-dev ecosystem audit-project my-api --path . --rule PS-SDK-WEB --json
```

The equivalent command was exercised against owned valid/invalid source
fixtures: exit 0 and exit 1 respectively, without executing consumer code.
The SDK's existing `scitex_dev.hooks` provider adds
`sdk.web-api-contract` before editor changes and
`sdk.web-api-contract-after-shell` after shell changes. Hook installation and
native client reload/consent remain the normal Dev workflow; declaration alone
does not prove a running client executed a hook. Post-shell checks report after
execution and cannot undo the shell operation.

The source reader parses owned modules and constants/reexports, with limits of
32 modules, 1 MB per module, 30,000 AST nodes per module, depth 40 and 20,000
evaluation steps per declaration. It never imports consumer modules or executes
handlers, arbitrary calls, comprehensions or dynamic factories. Conditional
rebinding, missing/foreign handlers, cycles, unsupported expressions and unknown
provenance produce explicit failures. Use a literal SDK descriptor or a justified
normal audit exception when a static contract genuinely cannot apply; do not
import the application to make inspection pass.

Validation reuses the SDK constructors and `ApiPlugin.openapi_fragment()`;
relative normalized routes, unique method/path claims, schema collisions,
operation IDs and existing scope/idempotency contracts keep one implementation.
A passing audit proves source declaration structure and handler binding syntax,
not runtime behavior, host enablement, authorization or live availability.

For inert distribution data, `api_mount.dump_inert_descriptor(plugin)` and
`api_mount.parse_inert_descriptor(text)` share the same validated constructors.
The existing installed-metadata reader uses `scitex_api.json` in dist-info and
delegates to the pure parser. Missing data remains unknown and never justifies
an import. Hosts still make an explicit `ApiAdmission` decision before resolving
or enabling handlers; neither the auditor nor hooks change that decision.
