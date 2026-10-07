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

## Sequential publication proposal

1. Close Dev's genuine project API and native release gates, then make a genuine
   Dev release at least 0.62 available publicly. Diagnostic SCM wheels below
   0.62 do not meet SDK's project/all floor. Dev's existing normal all/dev graph
   can resolve published dependencies; it does not require SDK 0.3 directly.
2. Publish SDK's genuine 0.3 including the reviewed optional project-selector
   normalization needed by migrated Writer/Hub, after its source/full suite, strict access,
   frontend, normal base/GUI, artifact/direct-ownership, and **normal built-wheel
   [all] install plus pip check** gates pass against published dependencies.
   During this bootstrap, report every transitive retired dist/import as
   `DEPENDENCY_RETIREMENT_NOT_READY`. A normal resolvable legacy graph is not a
   clean migration. Direct SDK ownership errors still block publication.
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
runtime groups also require UI>=0.23. SDK's all-extra still requires genuine
Dev>=0.62, which is currently unavailable and causes normal resolution refusal.
After Dev is published, that normal graph can remain legacy until canonical
FigRecipe, Scholar and the other owning consumers are genuinely published.

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

The 0.3.3 candidate raises optional CLI/project and contributor tooling to
Dev>=0.62.4.dev0 for the declared UI provider replacement SPI. The project
primitive itself existed in Dev 0.62, but an older engine would also discover
the incompatible SDK linter provider. `all` includes both tooling extras.
The paired Dev candidate is private, so a compatible public Dev release remains
a genuine prerequisite for normal SDK `[all]` publication. See
[the provider transition](UI_LINTER_PROVIDER_TRANSITION.md). No floor is lowered
to resolve the bootstrap.

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
