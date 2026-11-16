//! XLSX read/write wrapper for TNS Energy Studio.
//!
//! Uses umya-spreadsheet so the legacy source workbook can be loaded and
//! modified in place (like openpyxl) instead of being rebuilt from scratch.
//! The wrapper also ports legacy `safe_save_workbook`: write to a temp file,
//! replace the target atomically, and fall back to a timestamped copy when
//! Excel holds the target open.

use chrono::Local;
use std::fmt;
use std::path::{Path, PathBuf};
use umya_spreadsheet::{reader, writer, Workbook};

#[derive(Debug)]
pub enum ExcelError {
    Read(String),
    Write(String),
    Io(std::io::Error),
    Message(String),
}

impl fmt::Display for ExcelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ExcelError::Read(message) => write!(f, "Не удалось прочитать Excel: {}", message),
            ExcelError::Write(message) => write!(f, "Не удалось записать Excel: {}", message),
            ExcelError::Io(error) => write!(f, "IO: {}", error),
            ExcelError::Message(message) => write!(f, "{}", message),
        }
    }
}

impl std::error::Error for ExcelError {}

impl From<std::io::Error> for ExcelError {
    fn from(value: std::io::Error) -> Self {
        ExcelError::Io(value)
    }
}

pub type ExcelResult<T> = Result<T, ExcelError>;

pub const FALLBACK_WARNING: &str =
    "Основной файл открыт в Excel; результат сохранен в отдельную копию.";

pub fn read(path: impl AsRef<Path>) -> ExcelResult<Workbook> {
    reader::xlsx::read(path.as_ref()).map_err(|error| ExcelError::Read(error.to_string()))
}

pub fn write(book: &Workbook, path: impl AsRef<Path>) -> ExcelResult<()> {
    writer::xlsx::write(book, path.as_ref()).map_err(|error| ExcelError::Write(error.to_string()))
}

fn timestamp() -> String {
    Local::now().format("%Y%m%d_%H%M%S_%6f").to_string()
}

pub fn safe_save(
    book: &Workbook,
    target: impl AsRef<Path>,
) -> ExcelResult<(PathBuf, Option<String>)> {
    let target = target.as_ref().to_path_buf();
    let folder = target
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."));
    std::fs::create_dir_all(&folder)?;

    let temp = folder.join(format!(".tns-{}.xlsx", timestamp()));
    write(book, &temp)?;

    match std::fs::rename(&temp, &target) {
        Ok(()) => Ok((target, None)),
        Err(error) if error.kind() == std::io::ErrorKind::PermissionDenied => {
            let stem = target
                .file_stem()
                .map(|value| value.to_string_lossy().to_string())
                .unwrap_or_else(|| "result".into());
            let extension = target
                .extension()
                .map(|value| value.to_string_lossy().to_string())
                .unwrap_or_else(|| "xlsx".into());
            let fallback = folder.join(format!("{}_(копия_{}).{}", stem, timestamp(), extension));
            std::fs::rename(&temp, &fallback)?;
            Ok((fallback, Some(FALLBACK_WARNING.to_string())))
        }
        Err(error) => {
            let _ = std::fs::remove_file(&temp);
            Err(ExcelError::Io(error))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn fixture(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("tests")
            .join("parity")
            .join("fixtures")
            .join(name)
    }

    #[test]
    fn reads_fixture_values() {
        let book = read(fixture("dom_april_2026.xlsx")).expect("read fixture");
        let sheet = book.sheet(0).expect("active sheet");
        assert!(sheet.value("D1").contains("Южный Дом"));
        assert_eq!(sheet.value("A9"), "100");
        assert_eq!(sheet.value("I10"), "День");
        assert_eq!(sheet.value_number("AB9"), Some(152.75));
    }

    #[test]
    fn write_and_read_back() {
        let dir = tempfile::tempdir().expect("tempdir");
        let book = read(fixture("gorod_april_2026.xlsx")).expect("read fixture");
        let target = dir.path().join("copy.xlsx");
        write(&book, &target).expect("write");
        let again = read(&target).expect("read back");
        let sheet = again.sheet(0).expect("sheet");
        assert!(sheet.value("D1").contains("Южный Город"));
        assert_eq!(sheet.value_number("AB9"), Some(196.25));
    }

    #[test]
    fn safe_save_writes_target() {
        let dir = tempfile::tempdir().expect("tempdir");
        let book = read(fixture("dom_march_2026.xlsx")).expect("read fixture");
        let target = dir.path().join("result").join("dom.xlsx");
        let (saved, warning) = safe_save(&book, &target).expect("safe save");
        assert!(saved.is_file());
        assert!(warning.is_none());
    }
}
