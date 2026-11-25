---
description: |
  [TOPIC] Build from user intent
  [DETAILS] Turn a user's app idea into a scoped implementation and verification plan using existing leaf capabilities and shared SDK contracts.
  [WHEN] Use when the user describes what they want to build, such as a sample form, results dashboard or instrument log viewer, without requiring a starter choice.
  [HOW] Establish inputs, outputs, scope and acceptance examples; inspect existing providers; implement one useful interaction; verify behavior and installed delivery separately.
tags: [scitex-sdk-build-from-intent, app-development]
---

# Build from the user's intended outcome

Start with what the user wants to do. A starter choice is not a requirement
for this workflow. Reuse details already supplied; ask only about decisions
that affect behavior, permissions or data. Do not create another app when an
existing leaf capability can satisfy the request.

## Establish the first useful interaction

Record a short brief in the app's normal development instructions:

- Who uses it, and what task should become possible?
- What are the inputs and expected output, including a concrete example?
- Which project is in scope? Is all-project access appropriate and supported?
- What may be written, replaced or shared, and what must be refused?
- What observable result will demonstrate that the first interaction works?

Choose an interaction from that brief rather than a fixed catalog:

| User's outcome | First interaction | Acceptance examples |
| --- | --- | --- |
| Record experimental samples | Submit one sample and show the saved row | Valid fields round-trip; invalid input leaves existing data unchanged. |
| Explore analysis results | Select a result file and inspect its summary | Known fixture values match; empty or malformed files have useful feedback. |
| Inspect instrument logs | Open a log and filter its records | Matching records appear; clearing the filter restores the original set. |

These are planning examples, not generated features or separate templates.
Choose formats, domain algorithms and persistence with the owning leaf.
Keep domain rules there; SDK supplies shared application/UI/Web contracts,
Dev discovers and dispatches leaf checks, and Hub supplies host identity and
project services. Avoid copying those implementations into a new wizard.

## Inspect before creating

Read the relevant App/UI component skills and existing implementation.
Discover current interfaces with `scitex-sdk list-python-apis --json`,
`scitex-sdk skills list --json` and the component CLI help. Discovery output
does not prove a capability is enabled in the host or accepted for this task.

For an existing application, implement in its owned source and preserve data
identities, permissions and project confinement. For a new application, the
existing scaffold can supply boilerplate after the brief is settled:

```bash
scitex-sdk app init ./sample_app --name sample_app --dry-run
```

That command prints a plan without creating the application. Inspect the
chosen destination; remove `--dry-run` only when ready to create there. Do
not add `--overwrite` to work around an existing project. A scaffold creates
an application shell, not the form, analysis or viewer described above.
Existing leaf GUIs remain in their leaf-owned `_django` package; the scaffold
is not a migration instruction for those applications.

The current `scitex-sdk gui serve` creator still presents starter cards. Their
briefs describe intended work layered on the common scaffold; choosing a card
does not implement that feature. This skill does not replace that interface
or claim its starter UI has been removed. Reusable community workflows can be
added as skills when their implementation and acceptance evidence exist.

## Implement and verify the brief

Reuse SDK shell/header/project-scope primitives and leaf-owned data APIs.
Explicitly refuse unsupported scopes; make empty states and unavailable
inputs understandable. Preserve CSRF, authorization and path boundaries.
Implement the smallest complete interaction, then exercise its acceptance
examples on owned fixtures, including refusal and data-preservation cases.

Run `scitex-sdk app validate ./sample_app` for a newly created application.
Validation reports structural/readiness findings and advisory notices; it
does not prove the requested feature, security properties or visual behavior.
Run the owning behavioral tests as well. Check real UI states in the intended
host or standalone mode before claiming visual acceptance.

Verify the built wheel's skills, templates and assets through a normal private
installation. Source tests, installed discovery, host enablement and actual
served behavior are separate results. Record incomplete/manual coverage and
failures. Passing a build, importing a module or receiving HTTP200 is not
acceptance. Follow the existing release and host-admission workflow before
installation into a shared service, submission or publication.
