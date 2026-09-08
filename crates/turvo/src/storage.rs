// Copyright 2026 Turvo contributors
// SPDX-License-Identifier: Apache-2.0
// SPDX-License-Identifier: MIT

//! Servo storage-engine contracts exposed by Turvo.
//!
//! Applications provide factories through [`StorageEngines`]. Leaving a slot
//! empty preserves the backend built into the pinned Servo fork.

pub use storage_traits::StorageEngines;
pub use storage_traits::{
  cache_storage::{CacheStorageEngine, CacheStorageEngineFactory},
  client_storage::{RegistryEngine, RegistryEngineFactory},
  indexeddb::{IndexedDbEngineFactory, KvsEngine},
  webstorage_thread::{WebStorageEngine, WebStorageEngineFactory},
};
