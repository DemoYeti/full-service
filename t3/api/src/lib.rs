// Copyright (c) 2018-2023 MobileCoin, Inc.

//! T3 gRPC API.

use mc_util_uri::{Uri, UriScheme};

mod autogenerated_code {
    pub use protobuf::well_known_types::Empty;

    // Needed due to how to the auto-generated code references the Empty message.
    pub mod empty {
        pub use protobuf::well_known_types::Empty;
    }

    // Include the auto-generated code.
    include!(concat!(env!("OUT_DIR"), "/protos-auto-gen/mod.rs"));
}

pub use autogenerated_code::{t3::*, *};

pub type T3Uri = Uri<T3Scheme>;

/// T3 Uri Scheme
#[derive(Debug, Hash, Ord, PartialOrd, Eq, PartialEq, Clone)]
pub struct T3Scheme {}
impl UriScheme for T3Scheme {
    /// The part before the '://' of a URL.
    const SCHEME_SECURE: &'static str = "t3";
    const SCHEME_INSECURE: &'static str = "insecure-t3";

    /// Default port numbers
    const DEFAULT_SECURE_PORT: u16 = 443;
    const DEFAULT_INSECURE_PORT: u16 = 8080;
}