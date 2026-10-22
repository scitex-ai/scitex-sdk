"""manifest.json — schema and content."""

from __future__ import annotations

import json
import re
from pathlib import Path

# THE ONE REQUIRED-KEY LIST. scitex_sdk.app.validator imports this rather than
# declaring a second one — it declared its own for months, five keys against
# these six, so `license` was required by the CLI and not by AppValidator and
# nothing said so. Syncing two lists is a promise; importing one is a guarantee,
# and that promise had already been broken once here and once in the JS pattern
# list (0.16.2), both silently, both in the direction that disagrees about a
# peer's app.
#
# A TUPLE, not a list: this object is imported, so a list would be mutable
# shared state that any importer could `.append()` to, changing validation for
# every caller in the interpreter. (scitex-writer, 2026-09-06.)
MANIFEST_REQUIRED_KEYS = ("name", "slug", "label", "pip_package", "icon", "license")

#: Launcher-page sections a leaf may declare via the manifest ``group`` field.
#: CLOSED enum: anything else is a hard manifest ERROR (fail loud, per the
#: consuming-agent rules) rather than a silently mis-grouped tile. Lowercase
#: canonical, matched case-insensitively — the same convention as scope
#: (``_app_scope.VALID_SCOPES``). Omitted ``group`` is NOT an error: the host
#: keeps its existing grouping as the fallback, so adoption is per-leaf.
GROUP_FOUNDATION = "foundation"
GROUP_WORK = "work"
GROUP_PUBLICATION = "publication"
VALID_GROUPS = (GROUP_FOUNDATION, GROUP_WORK, GROUP_PUBLICATION)


def normalize_group(value: str | None) -> str | None:
    """Return the canonical launcher group for a raw manifest value.

    ``None`` / empty -> ``None`` (undeclared: the host keeps its existing
    grouping). A value already in :data:`VALID_GROUPS` (case-insensitive) is
    returned lower-cased. Any other value RAISES ``ValueError`` — a typo'd
    group must fail loud at validation/render, never degrade to a guessed
    launcher section.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    norm = str(value).strip().lower()
    if norm in VALID_GROUPS:
        return norm
    raise ValueError(
        f"manifest 'group' must be one of {VALID_GROUPS} (got {value!r}). "
        f"'group' declares the launcher-page section "
        f"(foundation / work / publication); omit it and the host keeps "
        f"its existing grouping."
    )


def validate_manifest(app_dir: str | Path) -> list[str]:
    """Check manifest.json schema and content."""
    errors = []
    root = Path(app_dir)
    manifest_path = root / "manifest.json"

    if not manifest_path.exists():
        return ["manifest.json not found"]

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return [f"manifest.json is not valid JSON: {e}"]

    if not isinstance(data, dict):
        return ["manifest.json must be a JSON object"]

    for key in MANIFEST_REQUIRED_KEYS:
        if key not in data:
            errors.append(f"manifest.json missing required key: '{key}'")

    # 'slug' IS the mount leaf (/apps/<slug>/): a malformed slug is a broken
    # URL, so the format is an ERROR, not advice. All five shipped leaves
    # (storage, scholar, writer, stats, create-app) already match.
    slug = data.get("slug", "")
    if slug and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errors.append(
            f"manifest.json 'slug' must be lowercase alphanumeric with single "
            f"hyphens (got: '{slug}') — it becomes /apps/<slug>/."
        )

    # The app version is the SINGLE SOURCE OF TRUTH: the installed package's own
    # version, read at runtime via importlib.metadata from `pip_package`. A
    # hand-written `version` in the manifest is FORBIDDEN — it inevitably drifts
    # from the package (2026-07 incident: manifests stuck at "0.14.0" while the
    # packages shipped 2.25.0 / 0.29.9 / 1.4.2, so every app tile showed a wrong
    # version). Declare `pip_package` (the dist name) and let the version derive.
    if "version" in data:
        errors.append(
            "manifest.json must NOT declare 'version' — it drifts from the "
            "package. The version is derived at runtime from the installed "
            "'pip_package' (importlib.metadata). Remove the 'version' key."
        )

    # 'scope' is OPTIONAL (absent -> "user", the safe no-selector default) but
    # when present it is a CLOSED enum: a typo'd scope must fail loud here,
    # not degrade to a guessed scope at render time. See _app_scope.py.
    if "scope" in data:
        from ..._app_scope import VALID_SCOPES

        scope = data["scope"]
        if not (isinstance(scope, str) and scope.strip().lower() in VALID_SCOPES):
            errors.append(
                f"manifest.json 'scope' must be one of {VALID_SCOPES} "
                f"(got {scope!r}). 'project' opts the app into a per-app "
                f"project selector; 'user' (or omit) renders with none."
            )

    # 'group' is OPTIONAL (absent -> undeclared, the host keeps its existing
    # grouping as the fallback) but when present it is a CLOSED enum: a typo'd
    # group must fail loud HERE, not degrade to a mis-grouped tile at render
    # time. Same convention as 'scope' above.
    if "group" in data:
        try:
            normalize_group(data["group"])
        except ValueError as exc:
            errors.append(f"manifest.json {exc}")

    # 'mobile_layout' is OPTIONAL and TRISTATE (ADR: mobile-layout card).
    # Semantics (hub-decided 2026-09-14): absent (None) = no claim — the hub
    # keeps its existing desktop-only metadata as the fallback; False =
    # explicitly desktop-only (the launcher badge is shown); True = a working
    # phone layout is declared (the badge disappears). It is a CLOSED bool
    # enum: any other value is a typo that must fail loud here, not degrade
    # to a guessed mobile state at render time. Making absent mean False is
    # forbidden — it would badge every existing (already mobile-working) app.
    if "mobile_layout" in data and not isinstance(data["mobile_layout"], bool):
        errors.append(
            f"manifest.json 'mobile_layout' must be true or false "
            f"(got {data['mobile_layout']!r}). Omit the key for 'no claim' "
            f"(the hub falls back to its existing metadata); false = "
            f"explicitly desktop-only; true = a working phone layout."
        )

    # 'mount_policy' is OPTIONAL (absent -> open mount, the back-compatible
    # default) but when present it is CLOSED: a file-touching plugin
    # without a jail block, a jail without the login boundary, or a typo'd
    # scope must fail loud HERE at scaffold/validate time — not as an open
    # mount in production. Delegates to the jail contract (scitex_sdk.app.jail)
    # so the validator and the mount-time bar judge by one implementation.
    if "mount_policy" in data:
        from ...jail import LeafContractError as _JailContractError
        from ...jail import validate_mount_policy as _validate_mount_policy

        try:
            _validate_mount_policy(data, plugin=data.get("name", "app"))
        except _JailContractError as exc:
            errors.append(f"manifest.json {exc}")

    # The 'name' suffix convention is ADVISORY and lives in
    # validate_manifest_advisory(), not here. See that function for why.

    return errors


def validate_manifest_advisory(app_dir: str | Path) -> list[str]:
    """Manifest findings that are ADVICE, not failures.

    A separate function rather than a severity argument on the one above, so the
    tier is STRUCTURAL: a finding is advisory because of where it is raised, not
    because of how its message happens to be worded. The name convention was
    worded "should" and enforced as a failure, which is how it became
    unclearable — scitex-scholar's manifest is `scholar_editor` because
    `scholar_app` would COLLIDE with hub's existing registry entry, so the only
    escape the rule offered was to create the bug the name avoids.
    """
    warnings = []
    root = Path(app_dir)
    manifest_path = root / "manifest.json"

    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []  # validate_manifest() already reports this, as an error
    if not isinstance(data, dict):
        return []

    name = data.get("name", "")
    if name and not (name.endswith("_app") or name.endswith("-app")):
        warnings.append(
            f"manifest.json 'name' should end with '_app' or '-app' (got: '{name}')"
        )

    # 'label' short tile form (operator 2026-10-23): the launcher page carries
    # the family brand, so tiles read Cards / Agent Container / Storage /
    # Scholar / Stats / FigRecipe / Writer — no 'SciTeX ' prefix. A prefixed
    # label is taste drift, so it is ADVICE: warn, never fail. Renaming a tile
    # is the App lane's call (leaf manifest + hub launcher entry).
    label = data.get("label", "")
    if label and label.startswith("SciTeX "):
        warnings.append(
            f"manifest.json 'label' should use the short tile form without "
            f"the 'SciTeX ' prefix (got: '{label}')"
        )

    # Favicon SSOT (operator 2026-10-20): the canonical mark is
    # scitex_sdk/ui/img/scitex-favicon.svg served via the shared
    # _branding_head.html partial. Leaf-local favicon files or hand-rolled
    # data-URI views are drift — advice to migrate, never a failure.
    _SKIP_DIRS = {"__pycache__", "node_modules", ".venv", ".git", ".old"}
    for path in sorted(root.rglob("*favicon*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        warnings.append(
            f"favicon drift: {path.name} should come from the SDK "
            f"(_branding_head.html + scitex-favicon.svg), not the leaf"
        )
        break  # one finding names the class; the list would just be long

    return warnings


# EOF
