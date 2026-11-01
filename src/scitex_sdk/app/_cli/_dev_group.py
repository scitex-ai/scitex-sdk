#!/usr/bin/env python3
"""The §13 ``dev`` group for ``scitex-sdk app`` and the §1a legacy alias.

Mirrors ``scitex_sdk.ui._dev_group``: the canonical home of the skills
surface is ``scitex-sdk app dev skills`` (operator directive, doctrine
20_dev-commands.md §13); the top-level ``scitex-sdk app skills`` spelling
stays as a Phase W warn-forward alias because §1a requires ``<cli> skills``
to exist while ``_skills/`` ships.

The alias shares the canonical group's subcommand objects rather than
re-declaring them, so the two spellings cannot drift apart. Like the ui
precedent it is plain click, not ``scitex_dev.ecosystem.deprecated_alias()``:
that helper imports scitex-dev, which is this package's optional ``[cli]``
extra, and routing a §1a-mandated command through it would break the
command for every install without the extra.
"""

from __future__ import annotations

import click

REMOVED_IN = "1.0.0"

CANONICAL = "scitex-sdk app dev skills"


class _WarnForwardMixin:
    """Phase W alias: works exactly as before, says where it moved.

    The warning goes to STDERR so it can never corrupt ``--json`` output
    being piped into something.
    """

    _canonical = ""
    _removed_in = ""

    def invoke(self, ctx):
        click.echo(
            f"DEPRECATED: `{ctx.command_path}` has moved to `{self._canonical}` "
            f"and this spelling is removed in {self._removed_in}. "
            f"Update to `{self._canonical}`; the two behave identically today.",
            err=True,
        )
        return super().invoke(ctx)


def register_dev_group(main: click.Group, skills_group: click.Group) -> click.Group:
    """Mount the canonical §13 ``dev`` group carrying ``skills``."""

    @main.group(name="dev")
    def dev_group():
        """Self-maintenance surfaces (§13). Group only — never takes an argument."""

    dev_group.add_command(skills_group, name="skills")
    return dev_group


def install_dev_aliases(main: click.Group, skills_group: click.Group) -> click.Group:
    """Mount the §1a legacy top-level ``skills`` spelling as warn-forward."""
    warn_forward_group = type("_WarnForwardGroup", (_WarnForwardMixin, click.Group), {})
    skills_alias = warn_forward_group(
        name="skills",
        commands=skills_group.commands,
        help=(
            f"DEPRECATED spelling of `{CANONICAL}`. Kept as a Phase W "
            f"warn-forward alias (removed in {REMOVED_IN}); use `{CANONICAL}`."
        ),
    )
    skills_alias._canonical = CANONICAL
    skills_alias._removed_in = REMOVED_IN
    main.add_command(skills_alias, name="skills")
    return skills_alias
