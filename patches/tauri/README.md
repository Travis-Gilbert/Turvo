# Runtime-owned new-window opener proposal

Status: versioned proposal, **not approved upstream and not used by Turvo's
published dependency graph**. Hosted compatibility results belong in
`docs/research/tauri-new-window.md` and the completion graph.

Base repository: [tauri-apps/tauri](https://github.com/tauri-apps/tauri).
Base tag: `tauri-v2.11.5`.
Exact base commit: `7cd71369c00978a3783b6ae3e9972358abbe4ae6`.

Patch: `0001-runtime-owned-new-window-opener.patch`.
SHA-256: `6e3bb64896d91b5704a7f06c27cb1638b0168cddf960a0104eba6e572c4c353a`.

The `Tauri opener patch` workflow checks out that exact public commit, applies
this patch, and runs the runtime tests, no-Wry core compilation, and Tauri's
default-runtime tests on Linux, macOS, and Windows. It does not push to Tauri.

To reproduce in a **clean checkout at the exact base**, use `git apply --check`
and then `git apply` with the absolute path to the patch. Run the same commands
as the workflow. The patch includes Tauri's required change-file entry; it does
not change package versions or claim a released API.

Before proposing this upstream, a human must review and test the change under
[Tauri's contribution policy](https://github.com/tauri-apps/tauri/blob/7cd71369c00978a3783b6ae3e9972358abbe4ae6/.github/CONTRIBUTING.md).
An approved public revision or release is a separate integration gate.
