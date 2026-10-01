"""`scitex-sdk ui skills` — list / get / install agent-facing skills.

Self-contained for its actual WORK: walks the package's own
`_skills/scitex-ui/` directory directly, with no scitex-dev runtime dep.

The structured HELP (§4b) is the one place scitex-dev is consulted, and it is
resolved lazily through `_cli_help` so the "no runtime dep" property still
holds — when the optional `[cli]` extra is absent these commands decorate as
plain click and render their docstrings. Nothing here imports scitex-dev at
module scope, which PS-213 forbids for anything reachable from the
console-script entry point.
"""

from __future__ import annotations

import os as _os
from pathlib import Path

import click

from ._cli_help import cli_help, examples as _examples, spec_command, spec_group

PKG = "scitex-ui"


def _skills_root() -> Path:
    """Resolve the bundled `_skills/scitex-ui/` directory."""
    from scitex_sdk import ui as scitex_ui

    pkg_dir = Path(scitex_ui.__file__).parent
    return pkg_dir / "_skills" / PKG


def _list_skill_files(root: Path) -> list[Path]:
    """All `.md` files under `_skills/scitex-ui/` (recursive), excluding SKILL.md."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file() and p.name != "SKILL.md")


@click.group(
    name="skills",
    invoke_without_command=True,
    **spec_group(
        cli_help(
            summary="Agent-facing skills bundled with scitex-ui.",
            description=(
                "Skills are markdown files shipped inside the package, so they "
                "travel with the installed version rather than a checkout.",
            ),
            examples=_examples(
                ("{prog} list", "what is bundled"),
                ("{prog} get 01_installation", "read one"),
                ("{prog} install", "materialise them for an agent"),
            ),
        ),
        command_categories=[
            ("Read", ["list", "get"]),
            ("Materialise", ["install"]),
        ],
    ),
)
@click.pass_context
def skills_group(ctx) -> None:
    """Agent-facing skills bundled with scitex-ui.

    \b
    Examples:
      $ scitex-sdk ui skills list
      $ scitex-sdk ui skills get 01_installation
      $ scitex-sdk ui skills install                  # → ~/.scitex/dev/skills/scitex-ui/
      $ scitex-sdk ui skills install --claude-symlink # also expose to ~/.claude/skills/scitex/
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@skills_group.command(
    name="list",
    **spec_command(
        cli_help(
            summary="List skill files bundled with this package.",
            description=(
                "Lists every .md under the bundled skills root except SKILL.md, "
                "which is the index rather than a skill.",
            ),
            examples=_examples(
                ("{prog}", ""),
                ("{prog} --json", "machine-readable"),
            ),
        )
    ),
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def skills_list(as_json: bool) -> None:
    """List skill files bundled with this package.

    \b
    Example:
      $ scitex-sdk ui skills list
      $ scitex-sdk ui skills list --json
    """
    root = _skills_root()
    files = _list_skill_files(root)
    if as_json:
        import json as _json

        click.echo(
            _json.dumps(
                [{"name": p.stem, "path": str(p)} for p in files],
                indent=2,
            )
        )
        return
    if not files:
        click.echo(f"no skills found at {root}", err=True)
        raise SystemExit(1)
    for p in files:
        rel = p.relative_to(root)
        click.echo(f"{p.stem:36s}  {rel}")


@skills_group.command(
    name="get",
    **spec_command(
        cli_help(
            summary="Print the contents of a skill file by NAME.",
            description=(
                "NAME is the stem shown by `skills list` (e.g. 01_installation); "
                "the .md extension is optional.",
            ),
            examples=_examples(
                ("{prog} 01_installation", ""),
                ("{prog} 01_installation --json", "wrapped for programmatic use"),
            ),
            see_also=("skills list",),
        )
    ),
)
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
def skills_get(name: str, as_json: bool) -> None:
    """Print the contents of a skill file by NAME (e.g. `01_installation`).

    \b
    Example:
      $ scitex-sdk ui skills get 01_installation
      $ scitex-sdk ui skills get 02_quick-start --json
    """
    root = _skills_root()
    target_stem = name[:-3] if name.endswith(".md") else name
    match = next((p for p in _list_skill_files(root) if p.stem == target_stem), None)
    if match is None:
        click.echo(f"skill not found: {name}", err=True)
        available = ", ".join(p.stem for p in _list_skill_files(root)[:8])
        click.echo(f"available: {available}…", err=True)
        raise SystemExit(1)
    if as_json:
        import json as _json

        click.echo(
            _json.dumps(
                {
                    "name": match.stem,
                    "path": str(match),
                    "content": match.read_text(encoding="utf-8"),
                },
                indent=2,
            )
        )
        return
    click.echo(match.read_text(encoding="utf-8"))


@skills_group.command(
    name="install",
    **spec_command(
        cli_help(
            summary="Materialise the bundled skills into a destination dir.",
            description=(
                "Symlinks by default so the installed copy follows package "
                "upgrades; --no-link copies instead, which is what you want "
                "when the destination must survive the package being removed.",
            ),
            examples=_examples(
                ("{prog}", "symlink into the default dir"),
                ("{prog} --dest ./skills --no-link", "copy to a chosen dir"),
            ),
            see_also=("skills list",),
        )
    ),
)
@click.option(
    "--dest",
    type=click.Path(),
    default=None,
    help="Destination dir (default: ~/.scitex/dev/skills/scitex-ui/).",
)
@click.option(
    "--no-link",
    "no_link",
    is_flag=True,
    help="Copy files instead of symlinking. Default is symlink.",
)
@click.option(
    "--claude-symlink",
    is_flag=True,
    help="Also expose at ~/.claude/skills/scitex/ for Claude Code consumers.",
)
@click.option("--dry-run", is_flag=True, help="Preview without copying/linking.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def skills_install(
    dest: str | None,
    no_link: bool,
    claude_symlink: bool,
    dry_run: bool,
    yes: bool,
) -> None:
    """Install this package's skills into a target directory.

    \b
    Default: symlink the entire `_skills/scitex-ui/` dir to
    ~/.scitex/dev/skills/scitex-ui/ so add/rename/delete in
    source propagates immediately.

    \b
    Example:
      $ scitex-sdk ui skills install
      $ scitex-sdk ui skills install --claude-symlink
      $ scitex-sdk ui skills install --no-link --dest /tmp/scitex-ui-skills
    """
    del yes  # accepted for §2 compliance; install is non-interactive
    src = _skills_root().resolve()
    if not src.is_dir():
        click.echo(f"no skills directory at {src}", err=True)
        raise SystemExit(1)

    base = (
        Path(dest).expanduser() if dest else Path.home() / ".scitex" / "dev" / "skills"
    )
    target = base / PKG

    if dry_run:
        action = "copy" if no_link else "symlink"
        click.echo(f"would {action} {src} → {target}")
        if claude_symlink:
            link = Path.home() / ".claude" / "skills" / "scitex"
            click.echo(f"would symlink {link} → {base}")
        return

    base.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        import shutil as _shutil

        _shutil.rmtree(target)

    if no_link:
        import shutil as _shutil

        _shutil.copytree(src, target)
        click.echo(f"copied {src} → {target}")
    else:
        _os.symlink(src, target, target_is_directory=True)
        click.echo(f"linked {target} → {src}")

    if claude_symlink:
        link = Path.home() / ".claude" / "skills" / "scitex"
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        if not link.exists():
            _os.symlink(base.resolve(), link, target_is_directory=True)
            click.echo(f"linked {link} → {base}")
        else:
            click.echo(
                f"warning: {link} exists and is not a symlink — skipping",
                err=True,
            )
