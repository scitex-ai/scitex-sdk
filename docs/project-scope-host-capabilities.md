# Host scope capabilities

A scoped project provider implements `current_scope(request)` and
`remember_scope(request, selection)`. Its optional
`user_scope_disabled_reason(request)` returns a nonempty reason to keep
All projects visible but disabled. Individual `ProjectEntry` values carry
`disabled=True` and `disabled_reason` for unavailable project choices.
The SDK listing view rejects both disabled kinds on POST.

The host can implement `project_provider_url(request, base_url)` to carry
app context in a shared provider endpoint. Both the canonical provider meta
tag and the project picker call this hook, including explicitly supplied
URLs. The host must apply its own explicit operational policy, preserve
project access checks, and never treat app context as authorization.
Calls without a request retain the original provider URL.

For scoped hosts, project picker tags advertise All projects and defer
availability to the server reason. Legacy project-only providers retain
their existing behavior. Picker CSS and JavaScript use `app_static`
content versions to avoid stale cached capability UI.

Evidence: `tests/scitex_sdk/ui/templatetags/test_scitex_project_picker.py`
checks matching meta/picker context, default scoped opt-in, legacy URLs,
and content-versioned assets. No transport or TypeScript change is needed;
the existing HTTP transport retains the configured URL for GET and POST.

Leaf manifests declare `scope_capabilities: {"user": true, "project": false}`
independently of storage `scope`. `ScitexAppConfig.scope_capabilities`
validates both literal booleans; omitted declarations make no support claim.
Hosts may restrict this support, never enable undeclared operations.
Optional `scope_capability_reasons` maps disabled kinds to explanatory text.
The generated starter explicitly declares user-only support because its
backend renders a user workspace and implements no project resource operations.
A leaf adding project operations must change its own declaration and tests.

Scoped host provider meta tags include `data-scoped-protocol="true"`.
`hostProjectProvider(document)` preserves that explicit host advertisement
through the shared HTTP transport, so manual SDK consumers receive disabled
All/project options too. An explicit `allowUserScope: false` still opts out;
metadata alone does not force a picker into a user-only app. The server GET
remains authoritative about protocol availability and disabled reasons.

Host shells must delegate provider metadata to the SDK tag, including mounted
app context and protocol advertisement. Repeated identical declarations in
a composed host/leaf document emit once; conflicting authorities raise.
Deduplication lasts for one outer Django template render, never a request
or later document.
