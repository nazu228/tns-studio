//! XLSX read/write wrapper for TNS Energy Studio.
//!
//! Uses umya-spreadsheet so the legacy source workbook can be loaded and
//! modified in place (like openpyxl) instead of being rebuilt from scratch.
//! The wrapper also ports legacy `safe_save_workbook`: write to a temp file,
//! replace the target atomically, and fall back to a timestamped copy when
//! Excel holds the target open.

use chrono::Local;
use std::fmt;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use umya_spreadsheet::{reader, writer};
pub use umya_spreadsheet::{
    new_file, Alignment, Border, Color, ConditionalFormatValues, ConditionalFormatting,
    ConditionalFormattingOperatorValues, ConditionalFormattingRule, Fill, Font, Formula,
    HorizontalAlignmentValues, Hyperlink, NumberingFormat, PatternFill, PatternValues,
    SequenceOfReferences, Style, VerticalAlignmentValues, Workbook, Worksheet,
};

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
    write_with_empty_inline(book, path, &[])
}

/// Write the workbook and mark legacy empty-string cells.
///
/// `empty_inline` holds `(sheet index, coordinate)` pairs. openpyxl writes a
/// cell created from an empty string as `<c r="A8" s="14" t="inlineStr"/>`;
/// umya has no inline-string writer and would emit `<c r="A8" s="14"/>`,
/// which openpyxl reports as a numeric cell. The post-process adds only the
/// `t="inlineStr"` attribute, leaving every value and style untouched.
pub fn write_with_empty_inline(
    book: &Workbook,
    path: impl AsRef<Path>,
    empty_inline: &[(usize, String)],
) -> ExcelResult<()> {
    let path = path.as_ref();
    writer::xlsx::write(book, path).map_err(|error| ExcelError::Write(error.to_string()))?;
    sanitize_xlsx(path, empty_inline)
}

fn zip_error(error: zip::result::ZipError) -> ExcelError {
    ExcelError::Write(error.to_string())
}

/// Remove empty `<diagonal/>` elements from borders that have styled sides.
///
/// umya always writes all five sides of every border. openpyxl omits the
/// diagonal element unless it is styled, so a styled border produced by umya
/// exposes an empty diagonal to the parity oracle while the legacy golden has
/// `diagonal=None`. Borderless cells keep their empty diagonal (it comes from
/// the source workbook's default border and must stay), so only borders with
/// at least one `style="..."` side are rewritten.
fn strip_empty_diagonals(xml: &str) -> String {
    let mut out = String::with_capacity(xml.len());
    let mut index = 0;
    while index < xml.len() {
        let Some(offset) = xml[index..].find("<border") else {
            out.push_str(&xml[index..]);
            break;
        };
        let start = index + offset;
        out.push_str(&xml[index..start]);
        let name_end = start + "<border".len();
        let is_element = matches!(xml.as_bytes().get(name_end), Some(b'>') | Some(b' '));
        if !is_element {
            // "<borders>" container.
            out.push_str("<border");
            index = name_end;
            continue;
        }
        let Some(open_offset) = xml[start..].find('>') else {
            out.push_str(&xml[start..]);
            break;
        };
        let open_end = start + open_offset + 1;
        if xml[start..open_end].ends_with("/>") {
            out.push_str(&xml[start..open_end]);
            index = open_end;
            continue;
        }
        let Some(close_offset) = xml[open_end..].find("</border>") else {
            out.push_str(&xml[start..]);
            break;
        };
        let inner_end = open_end + close_offset;
        let inner = &xml[open_end..inner_end];
        out.push_str(&xml[start..open_end]);
        if inner.contains(" style=\"") {
            out.push_str(&inner.replace("<diagonal/>", "").replace("<diagonal />", ""));
        } else {
            out.push_str(inner);
        }
        out.push_str("</border>");
        index = inner_end + "</border>".len();
    }
    out
}

fn mark_inline_string(xml: &str, coordinate: &str) -> String {
    let needle = format!("<c r=\"{}\"", coordinate);
    let Some(start) = xml.find(&needle) else {
        return xml.to_string();
    };
    let Some(offset) = xml[start..].find("/>") else {
        return xml.to_string();
    };
    let end = start + offset;
    let mut out = String::with_capacity(xml.len() + 13);
    out.push_str(&xml[..end]);
    out.push_str(" t=\"inlineStr\"");
    out.push_str(&xml[end..]);
    out
}

fn sheet_index(name: &str) -> Option<usize> {
    name.strip_prefix("xl/worksheets/sheet")
        .and_then(|rest| rest.strip_suffix(".xml"))
        .and_then(|number| number.parse::<usize>().ok())
        .and_then(|number| number.checked_sub(1))
}

fn sanitize_xlsx(path: &Path, empty_inline: &[(usize, String)]) -> ExcelResult<()> {
    let file = std::fs::File::open(path)?;
    let mut archive = zip::ZipArchive::new(file).map_err(zip_error)?;
    let temp = path.with_extension("tns-style.tmp");
    let mut writer = zip::ZipWriter::new(std::fs::File::create(&temp)?);
    let mut rewritten = false;

    for index in 0..archive.len() {
        let mut entry = archive.by_index(index).map_err(zip_error)?;
        let name = entry.name().to_string();
        let hints: Vec<&String> = sheet_index(&name)
            .map(|sheet| {
                empty_inline
                    .iter()
                    .filter(|(hint, _)| *hint == sheet)
                    .map(|(_, coordinate)| coordinate)
                    .collect()
            })
            .unwrap_or_default();

        if name == "xl/styles.xml" || !hints.is_empty() {
            let mut xml = String::new();
            entry.read_to_string(&mut xml)?;
            let mut cleaned = if name == "xl/styles.xml" {
                strip_empty_diagonals(&xml)
            } else {
                xml
            };
            for coordinate in hints {
                cleaned = mark_inline_string(&cleaned, coordinate);
            }
            rewritten = true;
            writer
                .start_file(name, zip::write::SimpleFileOptions::default())
                .map_err(zip_error)?;
            writer.write_all(cleaned.as_bytes())?;
        } else {
            writer.raw_copy_file(entry).map_err(zip_error)?;
        }
    }

    writer.finish().map_err(zip_error)?;
    if rewritten {
        std::fs::rename(&temp, path)?;
    } else {
        std::fs::remove_file(&temp)?;
    }
    Ok(())
}

fn timestamp() -> String {
    Local::now().format("%Y%m%d_%H%M%S_%6f").to_string()
}

pub fn safe_save(
    book: &Workbook,
    target: impl AsRef<Path>,
) -> ExcelResult<(PathBuf, Option<String>)> {
    safe_save_with_empty_inline(book, target, &[])
}

pub fn safe_save_with_empty_inline(
    book: &Workbook,
    target: impl AsRef<Path>,
    empty_inline: &[(usize, String)],
) -> ExcelResult<(PathBuf, Option<String>)> {
    let target = target.as_ref().to_path_buf();
    let folder = target
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."));
    std::fs::create_dir_all(&folder)?;

    let temp = folder.join(format!(".tns-{}.xlsx", timestamp()));
    write_with_empty_inline(book, &temp, empty_inline)?;

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

    #[test]
    fn strips_empty_diagonal_only_from_styled_borders() {
        let xml = concat!(
            r#"<border><left/><right/><top/><bottom/><diagonal/></border>"#,
            r#"<border><left style="thin"/><right style="thin"/><top style="thin"/>"#,
            r#"<bottom style="thin"/><diagonal/></border>"#,
            r#"<border><diagonal style="thin"><color rgb="00D3D3D3"/></diagonal></border>"#,
        );
        let cleaned = strip_empty_diagonals(xml);

        assert!(cleaned.contains(r#"<border><left/><right/><top/><bottom/><diagonal/></border>"#));
        assert!(cleaned.contains(r#"<bottom style="thin"/></border>"#));
        assert!(cleaned.contains(r#"<diagonal style="thin">"#));
    }

    #[test]
    fn marks_empty_cell_as_inline_string() {
        let xml = r#"<row r="8"><c r="A8" s="14"/><c r="B8" s="15" t="inlineStr"><is><t>x</t></is></c></row>"#;
        let cleaned = mark_inline_string(xml, "A8");

        assert!(cleaned.contains(r#"<c r="A8" s="14" t="inlineStr"/>"#));
        assert!(cleaned.contains(r#"<c r="B8" s="15" t="inlineStr"><is><t>x</t></is></c>"#));
    }
}
