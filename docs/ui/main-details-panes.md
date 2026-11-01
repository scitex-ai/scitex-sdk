# Main/details pane layout (unreleased source preview)

Opt a shared panes root into `data-stx-panes-layout="main-details"` when it has
`data-stx-pane="main"` and `data-stx-pane="details"` children. The existing SDK grid
owns desktop columns; the existing panes client owns phone pane switching.

The Details default is `--stx-panes-details-width: 320px`, bounded by
`--stx-panes-details-max-width: 40vw`. These are configuration tokens, not a new
leaf layout. A host-restored inline width wins while expanded. Setting
`data-stx-pane-collapsed` temporarily uses its content width without deleting
that inline value. On phones the active Details pane fills the available width
and the desktop maximum is removed. Other layout modes are unchanged.

This does not introduce width persistence: hosts that already restore widths
keep owning that storage. The existing panes client remembers the active pane.
The new mode is a source-preview addition beyond the published 0.3.16 contract;
consumers must qualify the future SDK release before publishing a new dependency
floor. Current preview package metadata intentionally stays 0.3.16.

Actual-browser candidate verification covered a 320px default, inline 400px
restoration, collapse to 61px, expansion back to 400px, a 641px viewport bound,
390px phone Details width, and return to the remembered desktop width.
