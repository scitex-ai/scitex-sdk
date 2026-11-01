# Contributing to scitex-sdk

Thank you for your interest in contributing to SciTeX. This guide covers the
process for reporting issues, suggesting features, and submitting code.

## Contributor License Agreement

Before your first contribution can be merged, you must agree to the
[SciTeX CLA](CLA.md). This is a one-time process. The CLA ensures that:

- You retain copyright of your work.
- The project can continue to offer dual licensing (free for researchers,
  commercial for enterprises).

See [CLA.md](CLA.md) for full details.

## Reporting Issues

- Search [existing issues](https://github.com/scitex-ai/scitex-sdk/issues)
  before opening a new one.
- Include a minimal reproducible example when reporting bugs.
- Specify your Python version, OS, and `scitex-sdk` version.

## Development Setup

```bash
git clone git@github.com:scitex-ai/scitex-sdk.git
cd scitex-sdk
python -m pip install --upgrade 'pip>=25.1'
python -m pip install -e ".[gui,chat,mcp,cli]" --group dev
```

## Branch Workflow

- `main` — stable releases only. Do not push directly.
- `develop` — integration branch; feature pull requests target it.
- Feature branches — create from `develop`, name as `feature/<description>`
  or `fix/<description>`.

```bash
git checkout develop
git checkout -b fix/my-change
# ... make changes ...
git push origin fix/my-change
# Open PR targeting develop
```

## Code Style

- Follow existing conventions in the codebase.
- Facade rule: `scitex_sdk.app` / `scitex_sdk.ui` re-export by **identity**
  (the same objects, never copies) — `tests/scitex_sdk/` enforces this.
- Keep files under 512 lines.
- Run tests before submitting:

```bash
pytest tests/ -x -q
```

## Pull Request Process

1. Ensure your branch is up to date with `develop`.
2. Write tests for new functionality.
3. Run the test suite and confirm all tests pass.
4. Open a PR targeting `develop` with a clear description.
   Accepted releases use a normal `develop` to `main` pull request; qualify
   that merged release commit before tagging it. See
   [the release procedure](docs/RELEASE_BOOTSTRAP.md).
5. The CLA bot will check your CLA status on your first PR.

## License

By contributing, you agree to the terms of the [CLA](CLA.md), which includes
licensing under AGPL-3.0 (see [LICENSE](LICENSE)) and the dual-licensing
provisions described therein.
