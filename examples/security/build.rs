// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

fn main() {
  tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
    tauri_build::AppManifest::new().commands(&[
      "protected_action",
      "binary_echo",
      "channel_echo",
      "emit_from_rust",
    ]),
  ))
  .expect("failed to build the native security fixture");
}
