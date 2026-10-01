#!/usr/bin/env python3
"""The §13 `dev` group and the §1a legacy `skills` alias.

Extracted from ``_cli.py`` (530 lines, over the 512 limit) so the entry-point
module holds wiring rather than doctrine. PR #165 proposed this same extraction
with these same two entry points on 2026-08-22; it went green, was never
merged, and drifted 29 commits behind while its FEATURE landed inline in
``_cli.py`` by another route. The naming here is that PR's, kept deliberately.

§13 vs §1a — TWO DOCTRINES ASK FOR OPPOSITE THINGS, and this module is where
they meet. Both are quoted rather than paraphrased, because the resolution only
makes sense if you can see that neither was ignored.

  §1a, 03_required-introspection-commands.md:98-104 —
    "If the package ships `_skills/<pkg>/`, `<cli> skills` exists as a group
     with `list`, `get`, and `install` subcommands. SELF-CONTAINED (no
     scitex-dev runtime dep) so users can introspect bundled skills without
     discovering the ecosystem-wide tooling first."

  §13, 20_dev-commands.md — `skills` is one of SIX FIXED verbs that mount under
    `dev`. The doctrine is explicit that the six NAMES are fixed even though
    the verbs inside each are not.

So §1a wants `scitex-sdk ui skills` to exist and §13 wants it gone from top level.

THE AUDITOR'S HINT DOES NOT WORK HERE. It offers
``scitex_dev.ecosystem.deprecated_alias()``, which imports scitex-dev — and
scitex-dev is this package's OPTIONAL [cli] extra (pyproject
``[project.optional-dependencies] cli``). Routing the §1a-mandated command
through it would hand that command a scitex-dev runtime dependency and break it
for every install without the extra, which is the exact thing §1a's
"self-contained" clause exists to prevent. The hint is right about the SHAPE and
wrong about the MECHANISM, so the alias below is plain click.

THE FLEET ALREADY SOLVED THIS, one line away in §1a's own file (:23), for
``list-python-apis``: "the legacy top-level mount stays as a Phase W
warn-forward alias during migration". Same collision, same answer — canonical
under ``dev``, legacy top level kept and warning.
"""

from __future__ import annotations

import click

from ._cli_help import cli_help, spec_group
from ._skills import skills_group as _skills_group

#: The version the legacy spelling stops working. ONE definition, used by both
#: the runtime warning and the `--help` text.
#:
#: IT WAS TWO, AND THEY BOTH SAID "0.20.0" WHILE 0.20.0 WAS THE SHIPPED
#: VERSION. The value lived here as a `_removed_in` attribute AND again as
#: literal prose inside the alias's help description, so the false claim
#: reached users twice from two places that nothing kept in agreement. A
#: version that appears in two hand-written strings is a second source of truth
#: (§1), and this is what that costs.
#:
#: A guard in tests/develop/test_dev_group_nests_skills.py now fails when this
#: is not strictly greater than pyproject's version. WHEN IT GOES RED, DO NOT
#: REFLEXIVELY BUMP IT — bumping is a treadmill unless the §1a/§13 question
#: above has been answered. §1a requires `<cli> skills` to EXIST while
#: `_skills/` ships, which may mean this spelling is never removable at all, in
#: which case it is a REQUIRED DUAL SPELLING and "removed in X" is false in
#: principle rather than merely early. See card
#: scitex-ui-deprecation-promises-removal-in-the-version-it-ships-in-20260904.
#:
#: DECIDED 2026-09-14 (0.21.0 release): §1a wins while `_skills/` ships, so the
#: legacy spelling cannot be removed in any 0.x release. 1.0.0 is the first
#: version allowed to break a §1a command; this is a decision, not a bump.
REMOVED_IN = "1.0.0"

CANONICAL = "scitex-sdk ui dev skills"

_DEV_HELP = cli_help(
    summary="Self-maintenance surfaces for this package.",
    description=(
        "Housekeeping, not domain: `scitex-sdk ui --help` should read as the tool, "
        "not as the tool's own upkeep (doctrine 20_dev-commands.md, §13).",
        "`dev` is a group only and never takes a positional argument directly.",
    ),
)

_SKILLS_ALIAS_HELP = cli_help(
    summary=f"DEPRECATED spelling of `{CANONICAL}`.",
    description=(
        "Kept as a Phase W warn-forward alias so nothing in the wild breaks "
        "mid-migration (§1a requires `<cli> skills` to exist while `_skills/` "
        f"ships; §13 wants it under `dev`). Removed in scitex-sdk ui {REMOVED_IN}.",
        f"Use `{CANONICAL}` — identical behaviour, no warning.",
    ),
)


class _WarnForwardMixin:
    """A Phase W alias: works exactly as before, says where it moved.

    Deliberately NOT a silent alias. A rename nobody is told about is
    discovered when it is REMOVED, which is the worst possible moment; the
    point of a Phase W window is that the warning arrives while both spellings
    still work.

    The warning goes to STDERR (§14) so it can never corrupt ``--json`` output
    being piped into something — that is the difference between a migration aid
    and the breakage it exists to avoid.

    A MIXIN rather than a base class because the base has to be chosen at
    import time: ``SpecGroup`` when scitex-dev is importable (so §4b's
    help-spec coverage sees a spec), plain ``click.Group`` when it is not (so
    §1a's self-contained rule still holds without the optional [cli] extra).
    Writing it as a mixin keeps ONE copy of the warning logic across both.
    """

    _canonical = ""
    _removed_in = ""

    def invoke(self, ctx):
        click.echo(
            f"DEPRECATED: `{ctx.command_path}` has moved to `{self._canonical}` "
            f"and this spelling is removed in scitex-sdk ui {self._removed_in}. "
            f"Update to `{self._canonical}`; the two behave identically today.",
            err=True,
        )
        return super().invoke(ctx)


def register_dev_group(main: click.Group) -> click.Group:
    """Mount the canonical §13 ``dev`` group on ``main`` and return it."""

    @click.group(name="dev", **spec_group(_DEV_HELP))
    def dev_group():
        """Self-maintenance surfaces (§13). Group only — never takes an argument."""

    dev_group.add_command(_skills_group, name="skills")
    main.add_command(dev_group, name="dev")
    return dev_group


def install_dev_aliases(main: click.Group, dev: click.Group) -> click.Group:
    """Mount the §1a legacy top-level ``skills`` spelling as a warn-forward alias.

    Shares the canonical group's subcommands rather than re-declaring them, so
    the two spellings cannot drift apart — a copy would be a second
    implementation, and the one that is not exercised is the one that rots.
    """
    alias_kwargs = spec_group(_SKILLS_ALIAS_HELP)
    alias_base = alias_kwargs.pop("cls", click.Group)
    warn_forward_group = type("_WarnForwardGroup", (_WarnForwardMixin, alias_base), {})

    skills_alias = warn_forward_group(
        name="skills",
        commands=_skills_group.commands,
        **alias_kwargs,
    )
    skills_alias._canonical = CANONICAL
    skills_alias._removed_in = REMOVED_IN
    main.add_command(skills_alias, name="skills")
    return skills_alias
