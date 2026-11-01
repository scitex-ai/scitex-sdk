# SDK publication and dependency retirement

This is a staged release-contract proposal. It does not publish anything, alter
repository protection, or certify that all consumers have migrated. Both predecessor repositories are
public and archived as observed on
2026-10-01 UTC, with source, refs, releases and artifacts preserved. Repository
archival does not remove published distributions or prove clean dependency
graphs.

SDK direct ownership is mandatory in every stage: canonical `scitex_sdk.app`
and `scitex_sdk.ui`, no top-level old module aliases, no SDK direct dependency on
retired App/UI distributions, and normal source/sdist/wheel/frontend identity.
Persisted Django labels/FKs, `scitex_ui` tag libraries, template blocks, existing
env names and local configuration/storage contracts remain unchanged.

## Current 0.3.17 release procedure

The source version is an unpublished preview until normal publication succeeds.
`pyproject.toml` requires Dev>=0.62.6 for CLI/project tooling and `[all]`;
old versions in the historical observations below are not current install floors.

1. Qualify the exact combined source. Stacked pull requests whose base is a
   feature branch do not trigger `frontend.yml` or `python-package.yml`: those
   PR events target `main`/`develop` only. Dispatch both existing workflows at
   the candidate branch, verify each run's `headSha`, or requalify after merging
   into a covered branch. An empty checks list is not a pass.
2. Review and merge the source in order, retaining the 0.3.17 Python/frontend
   versions and published dependency requirements. Do not tag an earlier base
   that omits the public PDF or request-local selection APIs.
3. Push `v0.3.17` at the accepted commit using the repository's release process.
   The tag triggers `pypi-publish-and-github-release-on-tag.yml`. Its manual
   dispatch accepts an already-existing tag; it does not create one.
4. Require the release's Python 3.11/3.12/3.13 tests, frontend gates, source/
   sdist/wheel/frontend identity checks, and normal built-wheel `[all]` install
   plus `pip check`. The ownership report explicitly distinguishes bootstrap
   observation from strict dependency retirement.
5. Publication uses the existing `pypi` environment and PyPI trusted publisher.
   Keep the workflow filename and environment identity. The GitHub release is
   created only after publication; verify the public distributions correspond
   to the accepted source before releasing LivePaper 0.2.20 and its Writer
   consumers. Retry an existing tag through the existing workflow only after
   classifying its actual failure; do not bypass a failed release gate.

The public dependency-retirement inventory remains a separate gate; SDK
publication does not certify migrated downstream graphs. See the historical
bootstrap observations and checker limitations below.

## Historical sequential publication proposal

1. (Done — Dev 0.62.4 is public.) Closed Dev's genuine project API and
   native release gates, then made the genuine Dev release 0.62
   publicly. Diagnostic SCM wheels below 0.62 do not meet SDK's
   project/all floor. Dev's existing normal all/dev graph
   can resolve published dependencies; it does not require SDK 0.3 directly.
2. (Done — SDK 0.3.x shipped through 0.3.12, verified live on PyPI after
   the normal built-wheel [all] + pip check gates passed.)
   The 0.3.3 declaration raised optional CLI/project and contributor tooling to
   Dev>=0.62 (Dev 0.62.4 public) for the declared UI provider replacement SPI.
   It shipped with the reviewed optional project-selector normalization needed
   by migrated Writer/Hub; transitive retired dists/imports were reported as
   `DEPENDENCY_RETIREMENT_NOT_READY` during bootstrap.
3. With SDK 0.3 publicly installable, release each accepted canonical consumer
   only after its native tests and normal install gates pass. Keep each actual
   active SDK>=0.3 declaration, including optional runtime groups. Register the
   genuine first canonical release and reviewed source/artifact association in
   `scripts/app-ui-retirement-graphs.json`; do not substitute invented versions
   or assume whichever release is latest contains the accepted source.
4. Run the independent dependency-retirement workflow. Every audited runtime or
   GUI graph resolves in its own new environment from public PyPI, passes pip
   check, declares its correct active SDK floor, and passes strict installed
   ownership inspection. The complete inventory also includes Template's core
   generator, Dev's all/dev graph, Config's retained environment contracts, and
   Clew's actual GUI. Native source/GUI/frontend controls and artifact provenance
   remain owning review gates. A per-graph pass never certifies global readiness.

This proposal changes only how a **transitive** old-owner observation affects
SDK bootstrap publication. It keeps normal all-extra resolution mandatory and
adds a separate strict retirement gate. Protected publishing jobs, full test
matrices, frontend workflow, release floors and artifact guards stay intact.
No release, dispatch, merge, tag, version override or archive runs here.

## Why Dev-first does not finish retirement

At the observed published versions, Dev 0.61 requires Scholar>=1.4.3; Scholar
1.13 requires Session>=0.1.5; Session 0.3.1 requires plt>=0.24; plt 0.24.6 requires
FigRecipe>=0.24. Published FigRecipe 0.35 directly requires App>=0.25. Its extra
runtime groups also require UI>=0.23. SDK's all-extra required genuine
Dev>=0.62; Dev 0.62.4 is now public so normal resolution succeeds, and
that graph can remain legacy until canonical FigRecipe, Scholar and the
other owning consumers are genuinely published.

FigRecipe canonical PR432 descends from the published v0.35.0 commit
`3b015a368761a1bf11c51d769774bc3f93c92edf`; the tag is an ancestor of develop
`8f11bdb76e4cd8d72aca1c358fea2d70ff265941` (+36 commits) and candidate
`b74e47e3b2ea9966e721c074349aac93b5cafc7d` (+37 commits). That pinned candidate
carried rolled-back 0.34.2 metadata despite retained
ancestry. PR432 now has a reviewed, unpublished 0.36.0 candidate at
`9446aa8c5295fd5e5dc5d16c4c6c2a86e3a7ffaa`; all package bytes match the reviewed
canonical parent. Its version correction is not a public release. A genuine
canonical release newer than published 0.35 must still register its source and
artifact association before dependency retirement can pass.

## Checker scope and remaining proof

`ownership_gate.py` inspects every installed distribution's metadata,
entry-point targets, packaged Python executable import/settings contexts,
literal frontend imports and npm dependency names. It also discovers old
module specs without importing them. Retired component names in canonical
SDK entry-point names and persisted labels are allowed; retired target modules
are rejected. Unreadable packaged source blocks strict retirement, and unreadable
SDK source or direct retired SDK edges also block bootstrap.

This static inventory does not execute providers, servers, GUI lifecycles or
arbitrary computed imports/eval/template expressions. Historical docs, skills
and test fixtures are excluded from executable inventory. Owning native tests
and source review are required to close those behaviors. The manually reviewed
source association in the policy is not Git provenance attested by pip.

Unregistered genuine release floors/commits, malformed inventory and missing
consumers fail before any resolver environment is created. Unpublished candidates are recorded as reviewed associations only. Their
canonical release versions and final release commits remain explicit nulls until
a genuine public release is registered. The current policy is intentionally
incomplete. Its failure is not skipped or converted into a
ready status. `app-ui-retirement.yml` is a read-only manual evidence workflow;
it has no publish, repository-admin or protection mutation job.
