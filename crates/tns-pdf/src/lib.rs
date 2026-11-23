//! PDFium-based parser for TNS electricity statements.
//!
//! The parser reads the vector grid of a statement table (page-space rules and
//! cell rectangles), extracts each table cell as text, and turns the rows into
//! a typed JSON document.

pub mod model;

/// Crate version.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
