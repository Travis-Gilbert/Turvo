# Public Tauri runtime integration patches

Status: public integration patches, **not approved upstream or registry-released**.
Hosted compatibility results belong in
`docs/research/tauri-new-window.md` and the completion graph.

Base repository: [tauri-apps/tauri](https://github.com/tauri-apps/tauri).
Base tag: `tauri-v2.11.5`.
Exact base commit: `7cd71369c00978a3783b6ae3e9972358abbe4ae6`.

Patch: `0001-runtime-owned-new-window-opener.patch`.
SHA-256: `6e3bb64896d91b5704a7f06c27cb1638b0168cddf960a0104eba6e572c4c353a`.

Patch 2: `0002-runtime-http-app-origins.patch`.
SHA-256: `46f4dbf6c76719216e9f195e81a9d568e800ce2a0667d3a0ac30400a26af521b`.
It adds the defaulted `Runtime::CUSTOM_PROTOCOLS_USE_HTTP` opt-in, coherent app
and `convertFileSrc` URLs, exact local authority checks, and isolation mapping.
Native Wry defaults remain unchanged. The runtime still supplies transport and
preserves browser policy; the opt-in grants no CORS exemption.

Both patches are published at
[`e847330`](https://github.com/Travis-Gilbert/tauri/commit/e84733018d84c8004645e04cbc8fea8511ae36b1)
on `turvo/integration-2.11.5`. `integration.json` records the exact source and
patch digests. They are development dependencies, not an upstream release.

The `Tauri opener patch` workflow checks out the exact base, applies both
patches in order, and runs runtime tests, no-Wry compilation, JavaScript URL
tests, default-runtime tests, and isolation-mode tests on Linux/macOS. Windows
is deferred by the user in Record 002, not passed. CI does not push to Tauri.

To reproduce in a **clean checkout at the exact base**, use `git apply --check`
and then `git apply` with the absolute path to the patch. Run the same commands
as the workflow. The patches include Tauri's required change-file entries; they do
not change package versions or claim a released API.

Before proposing this upstream, a human must review and test the change under
[Tauri's contribution policy](https://github.com/tauri-apps/tauri/blob/7cd71369c00978a3783b6ae3e9972358abbe4ae6/.github/CONTRIBUTING.md).
A registry-published revision remains a separate release gate.

The asset response's `Access-Control-Allow-Origin` still uses the initial
webview origin, as upstream does. A remote-first webview can therefore grant
that remote origin asset access. Applications must not treat this mapping as
a policy for running untrusted remote-first content with private bundled assets.
