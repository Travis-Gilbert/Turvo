// Copyright 2026 Turvo contributors
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

//! Servo storage-engine contracts exposed by Turvo.
//!
//! These reusable backend contracts remain available for downstream storage
//! implementations. Turvo's runtime uses Servo's built-in storage selection;
//! configuring custom factories through Turvo options is no longer supported.

pub use storage_traits::{
  cache_storage::{CacheStorageEngine, CacheStorageEngineFactory},
  client_storage::{RegistryEngine, RegistryEngineFactory},
  indexeddb::{IndexedDbEngineFactory, KvsEngine},
  webstorage_thread::{WebStorageEngine, WebStorageEngineFactory},
};
