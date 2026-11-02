# Main/details pane layout (experimental, available since SDK 0.3.17)

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
This opt-in mode is included in the published SDK 0.3.17 release. It remains
experimental: consumers must qualify the behavior against their declared SDK
minimum rather than rely on a source checkout. The 0.3.18 source metadata is
release preparation, not evidence that 0.3.18 is publicly available; verify the
normal release and official PyPI artifacts before declaring that newer floor.

Actual-browser candidate verification covered a 320px default, inline 400px
restoration, collapse to 61px, expansion back to 400px, a 641px viewport bound,
390px phone Details width, and return to the remembered desktop width.
