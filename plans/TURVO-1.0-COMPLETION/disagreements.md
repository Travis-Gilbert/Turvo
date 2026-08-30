# Decisions and disagreements

Canonical SHA-256: `e9df3f408ee5e698728df2b6f280bae0def4943a095982a1f4a94b1c48085c7d`

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

## ADR04: Can the Windows asset-routing tests also prove privileged IPC source authentication?

Choice: No. Refine the protocol work into asset routing and a separate source-authenticated IPC implementation with remote-frame and navigation-race native tests. Preserve the full O03/O04 release gate and never promote console-derived top-level URLs to trusted sender identity.

Reversibility: `reversible`

Retraction: Recombine the nodes only when the same engine-authenticated request surface and native receipts prove both boundaries.

## ADR05: Which published Servo surface can preserve bodies and authenticate privileged IPC without a console or origin fallback?

Choice: Use the pinned lower-level custom ProtocolHandler Request with engine Origin, client, and pipeline metadata. Read its body through ipc-channel's existing async stream adapter, reject nested and enforced-sandbox clients, bind opaque local identity to the served main-document pipeline, and revoke queued calls on navigation. Standard Tauri invokes use ipc:// on every OS; mapped HTTP never dispatches IPC. Native adversarial receipts remain required.

Reversibility: `reversible_with_cost`

Retraction: Remove the candidate adapter if native tests invalidate its provenance assumptions and propose a public Servo embedding API change. Never restore console-derived source identity. Consumer forks must patch servo and servo-net-traits coherently.

## ADR06: How should native CI handle the reproduced asset exposure and hosted Windows graphics limitations?

Choice: Use Servo's non-fetchable policy for ordinary custom assets and reserve the CORS exemption for source-authenticated IPC handlers. Reuse checksum-pinned Mesa as the Windows CI display driver without changing the product renderer or claiming hardware/ANGLE packaging proof. Keep custom-origin compatibility and the metadata-limited HTTP interception policy as engine-level release blockers.

Reversibility: `reversible_with_cost`

Retraction: Replace the restrictive protocol policy only after a public engine API enforces same-origin and CSP semantics with native positive/negative receipts. Remove CI Mesa if an equivalent native graphics runner is available.

## ADR07: What replaces the unsuccessful Mesa/WGL native probe?

Choice: Supersede ADR06's CI-driver branch with Servo's maintained no-wgl/ANGLE backend on Windows. Stage its own DLLs from current Cargo JSON build output, reject ambiguous or missing outputs, and retain the clean-machine package gate. Do not invent a graphics backend or claim that enabling the feature proves native behavior.

Reversibility: `reversible_with_cost`

Retraction: Revisit the backend selection only with native hardware evidence or a published Servo rendering API change; never remove the required Windows native gate.

## ADR08: How can W03 produce a reviewable upstream proposal without representing AI work as human-reviewed?

Choice: Use the versioned-public-patch path already allowed by W03, pinned to exact Tauri source and tested on all three desktop hosts in Turvo CI. Preserve the existing native opener signature, document the new runtime-only accessor tradeoff, and default-reject unsupported tokens. Do not submit an upstream PR until a human has reviewed and tested it under Tauri's contribution policy. E01 remains an accepted-release or explicitly approved-public-revision gate.

Reversibility: `reversible_with_cost`

Retraction: Revise or remove the proposal before adoption; Turvo's released dependency graph remains unchanged until E01 resolves.
