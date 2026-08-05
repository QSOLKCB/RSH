//! RSH parallel Frenet research surfaces.
//!
//! The accepted `RSH-FRENET-PARALLEL-V1` implementation remains in `lib.rs`.
//! This wrapper preserves that public API and adds the separately named local
//! shard-prefix reconstruction contract used before any multi-device work.

#[path = "lib.rs"]
mod parallel_v1;

pub use parallel_v1::*;

mod shard_prefix;

pub use shard_prefix::*;
