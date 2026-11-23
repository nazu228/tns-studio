//! PDFium-based parser for TNS electricity statements.
//!
//! The parser reads the vector grid of a statement table (page-space rules and
//! cell rectangles), extracts each table cell as text, and turns the rows into
//! a typed JSON document.

pub mod layout;
pub mod model;
pub mod parse;
pub mod pdfium;
pub mod text;
pub mod xlsx;

pub use parse::parse_pdf;
pub use xlsx::{unique_xlsx_file_name, write_statement_xlsx, write_statement_xlsx_with, xlsx_file_stem};

/// Crate version.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Parser error with enough context to locate a bad statement row.
#[derive(Debug)]
pub enum PdfError {
    Pdfium(pdfium::PdfiumError),
    Open {
        path: std::path::PathBuf,
        code: String,
    },
    Page {
        page: usize,
        message: String,
    },
    Parse {
        page: Option<usize>,
        house: Option<usize>,
        row: Option<usize>,
        message: String,
    },
    Invariant {
        page: Option<usize>,
        house: Option<usize>,
        row: Option<usize>,
        message: String,
    },
    Io(std::io::Error),
    NoStatements,
}

impl PdfError {
    pub fn invariant(
        message: impl Into<String>,
        page: Option<usize>,
        house: Option<usize>,
        row: Option<usize>,
    ) -> Self {
        Self::Invariant {
            page,
            house,
            row,
            message: message.into(),
        }
    }
}

impl std::fmt::Display for PdfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Pdfium(error) => write!(f, "{error}"),
            Self::Open { path, code } => {
                write!(f, "cannot open {}: {code}", path.display())
            }
            Self::Page { page, message } => write!(f, "page {page}: {message}"),
            Self::Parse {
                page,
                house,
                row,
                message,
            }
            | Self::Invariant {
                page,
                house,
                row,
                message,
            } => {
                let mut location = Vec::new();
                if let Some(page) = page {
                    location.push(format!("page={page}"));
                }
                if let Some(house) = house {
                    location.push(format!("house={house}"));
                }
                if let Some(row) = row {
                    location.push(format!("row={row}"));
                }
                if location.is_empty() {
                    write!(f, "{message}")
                } else {
                    write!(f, "{}: {message}", location.join(" "))
                }
            }
            Self::Io(error) => write!(f, "{error}"),
            Self::NoStatements => write!(f, "no TNS statements found"),
        }
    }
}

impl std::error::Error for PdfError {}

impl From<std::io::Error> for PdfError {
    fn from(error: std::io::Error) -> Self {
        Self::Io(error)
    }
}
