"""Focused workflow for an agent working on a generated custom app."""

def _agents_md(name, label, icon, description, frontend_type="html") -> str:
    return f"""# {label} development

Application: `{name}`. Purpose: {description or label}.
Frontend: {frontend_type}.

Read the scitex-sdk workflow skill and its App/UI contract before editing.
Check actual source, installed versions and runtime behavior; renew documents
when evidence contradicts them.

Keep this application's views, URLs, templates and assets together. Import
`scitex_sdk.app` and `scitex_sdk.ui`; never import Hub domain implementation.
The current custom-app scaffold keeps its compatible flat module layout.
Published leaf packages put their GUI under `src/<leaf_pkg>/_django`.

Use authorized host project/storage capabilities in plugin mode and an
explicit local root in standalone mode. Preserve refusal behavior, CSRF and
path confinement. Never use another user's files or rows for experiments.

Use `scitex-sdk app` and `scitex-sdk ui` commands within this skill workflow.
React components resolve via `@scitex/sdk/ui/...`; do not require a sibling
App/UI checkout. The frontend's generated `file:` dependency belongs to the
current Python environment: regenerate it and its lockfile after relocation.
The generated `.npmrc` packs that dependency with `install-links=true`.

Verify the installed wheel, template/static/npm exports and both mount modes.
Check desktop/mobile UI interactions before replacing an existing host route.
Release and deployment need their own verified artifact and host readiness.
"""
