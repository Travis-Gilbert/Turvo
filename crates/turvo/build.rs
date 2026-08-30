// Copyright 2019-2024 Tauri Programme within The Commons Conservancy
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

// creates a cfg alias if `has_feature` is true.
// `alias` must be a snake case string.
fn alias(alias: &str, has_feature: bool) {
  println!("cargo:rustc-check-cfg=cfg({alias})");
  if has_feature {
    println!("cargo:rustc-cfg={alias}");
  }
}

fn main() {
  let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap();
  let mobile = target_os == "ios" || target_os == "android";
  alias("desktop", !mobile);
  alias("mobile", mobile);

  if target_os == "windows" {
    embed_windows_manifest();
  }
}

// Tauri enables Microsoft Common Controls v6, whose entry points are selected
// through an application manifest. A library build script must emit these
// arguments itself so downstream binaries and integration tests receive the
// manifest too.
fn embed_windows_manifest() {
  let manifest =
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("windows-app-manifest.xml");

  println!("cargo:rerun-if-changed={}", manifest.display());
  println!("cargo:rustc-link-arg=/MANIFEST:EMBED");
  println!("cargo:rustc-link-arg=/MANIFESTINPUT:{}", manifest.display());
  println!("cargo:rustc-link-arg=/WX");
}
