# Coming from `scitex-app` or `scitex-ui`

Both predecessors are **public archives** (read-only) and receive no
updates:

- [scitex-ai/scitex-app](https://github.com/scitex-ai/scitex-app) — app
  code now lives in `scitex_sdk.app`.
- [scitex-ai/scitex-ui](https://github.com/scitex-ai/scitex-ui) — UI code
  now lives in `scitex_sdk.ui`.

Active development continues here, in `scitex-sdk`.

## Install

```bash
pip install 'scitex-sdk[gui]>=0.3.0'
```

Add the `chat`, `mcp`, `cli` or `project` extras for those capabilities,
or install `scitex-sdk[all]`. The `project` and `all` extras require
`scitex-dev>=0.62.0`.

## What moved where

| Before | Now |
| --- | --- |
| `scitex-app` package | `scitex_sdk.app` |
| `scitex-ui` package | `scitex_sdk.ui` |
| app template/static paths | `scitex_sdk/app/...` |
| ui template/static paths | `scitex_sdk/ui/...` |

## What stayed the same

- Django database labels (`scitex_app`, `scitex_ui`).
- The `scitex_app_content` template block and template tag library
  filenames.
- Existing `SCITEX_APP_*` / `SCITEX_UI_*` settings and configuration
  locations.

## Next steps

- App/UI contract and leaf integration:
  [src/scitex_sdk/_docs/APP_DEVELOPER_GUIDE.md](../src/scitex_sdk/_docs/APP_DEVELOPER_GUIDE.md).
- Release sequence and dependency-retirement gates:
  [docs/RELEASE_BOOTSTRAP.md](RELEASE_BOOTSTRAP.md).
