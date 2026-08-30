# Decisions and disagreements

Canonical SHA-256: `13e1eb23cc113380065dc2a0f29957978d859bb8dac12bac2f301935b2b65e1d`

These decisions resolve known design forks. A failed oracle reopens the named decision through its retraction path rather than weakening acceptance.

## ADR01: How should Windows Tauri app URLs reach bundled assets without weakening origin classification?

Choice: Intercept only Tauri-owned localhost HTTP(S) requests through Servo WebResourceLoad, route them to the registered protocol handler, and preserve the browser-visible URL as the IPC and capability origin.

Reversibility: `reversible_with_cost`

Retraction: Remove the interception adapter after Tauri exposes a runtime-neutral app URL or Servo supports an equivalent registered-scheme mapping on Windows.

## ADR02: How should Turvo satisfy NewWindowOpener without fabricating Wry objects?

Choice: Contribute or adopt an additive runtime-neutral Tauri new-window seam, test it upstream, and integrate only a released or explicitly versioned public patch; unsafe placeholders are forbidden.

Reversibility: `reversible_with_cost`

Retraction: Keep window.open blocked and retain command-created windows if upstream rejects the seam; reopen the API design with the rejection evidence.

## ADR03: When should the imported 5,000-line runtime be split and turvo-build introduced?

Choice: First establish current-tip behavior tests, then extract modules without behavior changes; make turvo-build stage only resources demonstrated necessary by clean-machine bundle evidence.

Reversibility: `reversible`

Retraction: Recombine a module or remove an unnecessary staging rule while retaining the behavior tests.
