"""Compose SDK maintenance routes from the owning leaf command providers."""

import click


def _register_dev_group(main: click.Group, ui: click.Group) -> None:
    """Share real commands; retain existing root and UI compatibility paths."""
    dev = click.Group(
        name="dev",
        help=(
            "SDK maintenance: UI lint plus installed docs and skills providers. "
            "Lint uses SDK-owned rules; docs/skills require optional scitex-dev."
        ),
    )
    dev.add_command(ui.commands["lint"], "lint")
    try:
        from scitex_dev.cli import docs_click_group, skills_click_group

        # Construct each package-scoped provider once. Both paths invoke it.
        docs = docs_click_group(package="scitex-sdk")
        skills = skills_click_group(package="scitex-sdk")
        for name, command in (("docs", docs), ("skills", skills)):
            main.add_command(command, name)
            dev.add_command(command, name)
    except ImportError:
        pass
    main.add_command(dev)
