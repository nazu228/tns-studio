//! Standard TNS workbook writer for parsed PDF statements.
//!
//! The PDF parser produces a typed `Statement`. This module projects it onto
//! the legacy 1C source layout (row types 100/101/102 plus the required column
//! headers) and lets `tns-core::process_statement` build the regular output
//! workbook: `Сводка по домам` + `Ведомость ЭП` with formulas and styles.

use crate::model::{House, Meter, Statement};
use crate::PdfError;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tns_core::{ProcessOptions, ProcessResult};
use tns_excel::{new_file, Worksheet};

const HEADER_ROW: usize = 8;
const FIRST_DATA_ROW: usize = 9;

/// Build the output file stem for a statement.
///
/// Normal statements use `<contract>_<Month>_<Year>`; corrections append
/// `_за_<BaseMonth>_<BaseYear>` so several corrections of one period cannot
/// overwrite each other.
pub fn xlsx_file_stem(statement: &Statement) -> Result<String, PdfError> {
    let contract = statement
        .statement
        .contract
        .clone()
        .unwrap_or_else(|| statement.statement.kind.clone());
    let (month, year) = document_month_year(statement)?;
    let mut stem = format!("{contract}_{month}_{year}");
    if let Some(base) = statement.statement.base_period.as_deref() {
        let (base_month, base_year) = period_parts(base)?;
        let base_name = month_name(base_month)?;
        stem.push_str(&format!("_за_{base_name}_{base_year}"));
    }
    Ok(stem)
}

/// Build a unique output file name for one PDF run.
///
/// Two statements of the same contract and period (for example two
/// corrections) would otherwise overwrite each other, so the second name
/// gets `_2`, the third `_3`, and so on.
pub fn unique_xlsx_file_name(
    statement: &Statement,
    used: &mut HashSet<String>,
) -> Result<String, PdfError> {
    let stem = xlsx_file_stem(statement)?;
    let mut name = stem.clone();
    let mut counter = 2;
    while !used.insert(name.clone()) {
        name = format!("{stem}_{counter}");
        counter += 1;
    }
    Ok(format!("{name}.xlsx"))
}

/// Write one parsed statement as the standard TNS workbook.
///
/// `file_name` is passed to `tns-core` as the custom output name; the source
/// projection itself is a temporary file and is removed afterwards.
pub fn write_statement_xlsx(
    statement: &Statement,
    output_dir: &Path,
    file_name: &str,
) -> Result<ProcessResult, PdfError> {
    write_statement_xlsx_with(statement, output_dir, file_name, None, None)
}

/// Same as [`write_statement_xlsx`], but forwards progress and cancellation
/// callbacks to `tns-core::process_statement` so a desktop app can stream
/// updates and stop a long PDF run.
pub fn write_statement_xlsx_with(
    statement: &Statement,
    output_dir: &Path,
    file_name: &str,
    progress: Option<&dyn Fn(u8, &str)>,
    cancel: Option<&dyn Fn() -> bool>,
) -> Result<ProcessResult, PdfError> {
    let source = write_source_projection(statement)?;
    let (month, year) = document_month_year(statement)?;
    let result = tns_core::process_statement(
        &source,
        ProcessOptions {
            output_dir: Some(output_dir.to_path_buf()),
            custom_filename: Some(file_name.to_string()),
            month: Some(month),
            year: Some(year),
            progress,
            cancel,
        },
    )
    .map_err(|error| projection_error(error.to_string()))?;
    let _ = std::fs::remove_file(&source);
    Ok(result)
}

fn write_source_projection(statement: &Statement) -> Result<PathBuf, PdfError> {
    // `new_file` initializes the default theme/stylesheet so the generated
    // workbook loads in Excel/openpyxl without a "no default style" warning.
    let mut book = new_file();
    let sheet = book
        .sheet_mut(0)
        .map_err(|error| projection_error(error.to_string()))?;
    sheet.set_name("Ведомость");

    write_metadata(sheet, statement);
    write_headers(sheet);

    let mut row = FIRST_DATA_ROW;
    for house in &statement.houses {
        write_house_row(sheet, house, row)?;
        row += 1;
        for meter in house_meters(statement, house) {
            write_meter_row(sheet, meter, row);
            row += 1;
        }
    }
    write_total_row(sheet, statement, row)?;

    let directory = std::env::temp_dir().join("tns-pdf");
    std::fs::create_dir_all(&directory).map_err(|error| PdfError::Io(error))?;
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_nanos())
        .unwrap_or(0);
    let source = directory.join(format!("source-{unique}.xlsx"));
    tns_excel::write(&book, &source).map_err(|error| projection_error(error.to_string()))?;
    // umya omits the default `Normal` cell style entries for workbooks created
    // from scratch; without them Excel/openpyxl treat the file as damaged.
    tns_excel::ensure_default_cell_styles(&source)
        .map_err(|error| projection_error(error.to_string()))?;
    Ok(source)
}

fn write_metadata(sheet: &mut Worksheet, statement: &Statement) {
    if let Some(org) = statement.statement.org.as_deref() {
        set_text(sheet, 1, 1, org);
    }
    if let Some(contract) = statement.statement.contract.as_deref() {
        set_text(sheet, 1, 2, &format!("Договор: {contract}"));
    }
    if let Some(month) = statement.statement.month_label.as_deref() {
        set_text(sheet, 1, 3, &format!("Месяц: {month}"));
    }
    set_text(sheet, 1, 4, "Ведомость электропотребления");
}

fn write_headers(sheet: &mut Worksheet) {
    set_text(sheet, 1, HEADER_ROW, "Тип");
    set_text(sheet, 3, HEADER_ROW, "Номер");
    set_text(sheet, 4, HEADER_ROW, "Наименование");
    set_text(sheet, 5, HEADER_ROW, "Заводской номер");
    set_text(sheet, 9, HEADER_ROW, "Зона тарифа");
    set_text(sheet, 10, HEADER_ROW, "Субабонент");
    set_text(sheet, 12, HEADER_ROW, "Нач");
    set_text(sheet, 13, HEADER_ROW, "Кон");
    set_text(sheet, 15, HEADER_ROW, "Разность");
    set_text(sheet, 16, HEADER_ROW, "Коэф");
    set_text(sheet, 17, HEADER_ROW, "Основной расход");
    set_text(sheet, 23, HEADER_ROW, "Вычитание по суб");
    set_text(sheet, 28, HEADER_ROW, "Начисленный объем");
}

fn write_house_row(sheet: &mut Worksheet, house: &House, row: usize) -> Result<(), PdfError> {
    set_text(sheet, 1, row, "100");
    set_text(sheet, 3, row, &house.name);
    let control = house
        .control
        .ok_or_else(|| projection_error(format!("house {} has no control value", house.num)))?;
    set_number(sheet, 28, row, control);
    Ok(())
}

fn write_meter_row(sheet: &mut Worksheet, meter: &Meter, row: usize) {
    set_text(sheet, 1, row, if meter.is_sub { "102" } else { "101" });
    set_text(sheet, 3, row, &meter.point);
    set_text(sheet, 4, row, &meter.place);
    set_text(sheet, 5, row, &meter.serial);
    set_text(sheet, 9, row, &meter.zone_raw);
    set_text(sheet, 10, row, &meter.sub_type);
    set_optional(sheet, 12, row, meter.start);
    set_optional(sheet, 13, row, meter.end);
    set_optional(sheet, 15, row, meter.delta);
    set_optional(sheet, 16, row, meter.k);
    set_optional(sheet, 17, row, meter.main);
    set_optional(sheet, 23, row, meter.sub_volume);
    set_number(sheet, 28, row, meter.billed.unwrap_or(0.0));
}

fn write_total_row(
    sheet: &mut Worksheet,
    statement: &Statement,
    row: usize,
) -> Result<(), PdfError> {
    let volume =
        statement.totals.official.volume.ok_or_else(|| {
            projection_error("statement has no official total volume".to_string())
        })?;
    set_text(sheet, 1, row, "100");
    set_text(sheet, 3, row, "Итого:");
    set_number(sheet, 28, row, volume);
    Ok(())
}

fn house_meters<'a>(statement: &'a Statement, house: &'a House) -> impl Iterator<Item = &'a Meter> {
    let meters = &statement.meters;
    let (start, end) = (house.meter_range[0], house.meter_range[1]);
    meters
        .iter()
        .skip(start)
        .take(end.saturating_sub(start) + 1)
}

fn document_month_year(statement: &Statement) -> Result<(String, String), PdfError> {
    let label = statement
        .statement
        .month_label
        .as_deref()
        .ok_or_else(|| projection_error("statement has no month label".to_string()))?;
    let mut words = label.split_whitespace();
    let month = words
        .next()
        .ok_or_else(|| projection_error("month label has no month".to_string()))?
        .to_string();
    let year = words
        .next()
        .ok_or_else(|| projection_error("month label has no year".to_string()))?
        .to_string();
    Ok((month, year))
}

fn period_parts(period: &str) -> Result<(u32, String), PdfError> {
    let (year, month) = period
        .split_once('-')
        .ok_or_else(|| projection_error(format!("bad period `{period}`")))?;
    let month = month
        .parse::<u32>()
        .map_err(|_| projection_error(format!("bad period month `{month}`")))?;
    Ok((month, year.to_string()))
}

fn month_name(month: u32) -> Result<String, PdfError> {
    const MONTHS: [&str; 12] = [
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ];
    MONTHS
        .get(month as usize - 1)
        .map(|name| name.to_string())
        .ok_or_else(|| projection_error(format!("bad month number `{month}`")))
}

fn set_text(sheet: &mut Worksheet, column: usize, row: usize, value: &str) {
    // PDFium can emit control characters (for example STX inside street names)
    // that are illegal in XML; strip them before the value reaches umya.
    let cleaned: String = value
        .chars()
        .filter(|character| {
            !matches!(
                *character as u32,
                0x00..=0x08 | 0x0B | 0x0C | 0x0E..=0x1F
            )
        })
        .collect();
    sheet
        .cell_mut((column as u32, row as u32))
        .set_value_string(&cleaned);
}

fn set_number(sheet: &mut Worksheet, column: usize, row: usize, value: f64) {
    sheet
        .cell_mut((column as u32, row as u32))
        .set_value_number(value);
}

fn set_optional(sheet: &mut Worksheet, column: usize, row: usize, value: Option<f64>) {
    if let Some(value) = value {
        set_number(sheet, column, row, value);
    }
}

fn projection_error(message: String) -> PdfError {
    PdfError::Parse {
        page: None,
        house: None,
        row: None,
        message,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Balance, Layout, Official, PageInfo, Source, StatementMeta, Totals};

    fn statement_fixture() -> Statement {
        let house = House {
            num: 1,
            name: "ул. Тестовая, 1".to_string(),
            page: 1,
            main: Some(100.0),
            sub_deduct: None,
            control: Some(150.0),
            amount: Some(1000.0),
            day: 100.0,
            night: 0.0,
            odn: 50.0,
            simple: 50.0,
            total: 150.0,
            diff: 0.0,
            meters_active: 2,
            meters_res: 0,
            sub_rows: 0,
            meter_range: [0, 1],
        };
        let meters = vec![
            Meter {
                house: 1,
                row: 1,
                page: 1,
                point: "230110601001".to_string(),
                place: "ОДПУ МКД ввод 1".to_string(),
                serial: "0123456789".to_string(),
                zone: "day".to_string(),
                zone_raw: "День".to_string(),
                preview_bucket: "day".to_string(),
                sub_type: String::new(),
                start: Some(100.0),
                end: Some(200.0),
                delta: Some(100.0),
                k: Some(1.0),
                main: Some(100.0),
                extra: None,
                unmetered: None,
                odn: None,
                line_loss: None,
                tr_loss: None,
                sub_volume: None,
                voltage: "НН".to_string(),
                category: "Городское ЭП".to_string(),
                billed: Some(100.0),
                amount: Some(700.0),
                is_sub: false,
                is_reserve: false,
            },
            Meter {
                house: 1,
                row: 2,
                page: 1,
                point: "230110601002".to_string(),
                place: "ОДПУ МКД ввод 2".to_string(),
                serial: "0987654321".to_string(),
                zone: "odn".to_string(),
                zone_raw: String::new(),
                preview_bucket: "odn".to_string(),
                sub_type: String::new(),
                start: Some(10.0),
                end: Some(60.0),
                delta: Some(50.0),
                k: Some(1.0),
                main: Some(50.0),
                extra: None,
                unmetered: None,
                odn: None,
                line_loss: None,
                tr_loss: None,
                sub_volume: None,
                voltage: "НН".to_string(),
                category: "Городское ЭП".to_string(),
                billed: Some(50.0),
                amount: Some(300.0),
                is_sub: false,
                is_reserve: false,
            },
        ];
        Statement {
            schema_version: Statement::SCHEMA_VERSION,
            source: Source {
                file: "fixture.pdf".to_string(),
                pages: 1,
                producer: Some("test".to_string()),
                text_layer: true,
            },
            statement: StatementMeta {
                kind: "gorod".to_string(),
                is_correction: false,
                org: Some("ООО \"Южный город\"".to_string()),
                contract: Some("23110604327".to_string()),
                month: Some("2026-10".to_string()),
                base_period: None,
                month_label: Some("Октябрь 2026".to_string()),
                page_range: [1, 1],
            },
            layout: Layout {
                page_size: [841.89, 595.28],
                columns: 27,
                x_boundaries: Vec::new(),
                confidence: 1.0,
            },
            pages: vec![PageInfo {
                page: 1,
                footer: None,
                rows: 4,
                houses_started: 1,
                role: "title+table".to_string(),
            }],
            houses: vec![house],
            meters,
            totals: Totals {
                day: 100.0,
                night: 0.0,
                odn: 50.0,
                control: 150.0,
                amount: 1000.0,
                official: Official {
                    volume: Some(150.0),
                    amount: Some(1000.0),
                    page: Some(1),
                },
                balance: Balance {
                    volume: 0.0,
                    amount: 0.0,
                },
            },
            warnings: Vec::new(),
        }
    }

    #[test]
    fn names_files_by_contract_and_period() {
        let mut statement = statement_fixture();
        assert_eq!(
            xlsx_file_stem(&statement).expect("stem"),
            "23110604327_Октябрь_2026"
        );
        statement.statement.is_correction = true;
        statement.statement.base_period = Some("2026-09".to_string());
        assert_eq!(
            xlsx_file_stem(&statement).expect("stem"),
            "23110604327_Октябрь_2026_за_Сентябрь_2026"
        );
    }

    #[test]
    fn duplicate_statements_get_numbered_file_names() {
        let statement = statement_fixture();
        let mut used = HashSet::new();
        assert_eq!(
            unique_xlsx_file_name(&statement, &mut used).expect("first name"),
            "23110604327_Октябрь_2026.xlsx"
        );
        assert_eq!(
            unique_xlsx_file_name(&statement, &mut used).expect("second name"),
            "23110604327_Октябрь_2026_2.xlsx"
        );
        assert_eq!(
            unique_xlsx_file_name(&statement, &mut used).expect("third name"),
            "23110604327_Октябрь_2026_3.xlsx"
        );
    }

    #[test]
    fn writes_standard_workbook_from_statement() {
        let statement = statement_fixture();
        let directory = tempfile::tempdir().expect("tempdir");
        let seen: std::sync::Mutex<Vec<(u8, String)>> = std::sync::Mutex::new(Vec::new());
        let cancelled = [false; 1];
        let result = write_statement_xlsx_with(
            &statement,
            directory.path(),
            "23110604327_Октябрь_2026.xlsx",
            Some(&|percent, message| {
                seen.lock().expect("progress lock").push((percent, message.to_string()));
            }),
            Some(&|| cancelled[0]),
        )
        .expect("write statement");
        assert!(result.success);
        assert_eq!(result.houses_count, 1);
        assert_eq!(result.total_day, 100.0);
        assert_eq!(result.total_odn, 50.0);
        assert_eq!(result.total_all, 150.0);
        assert_eq!(result.statement_total, 150.0);
        assert!(result.balance_ok);
        assert!(Path::new(&result.target_path).is_file());
        let seen = seen.into_inner().expect("progress lock");
        assert!(
            seen.iter().any(|(percent, _)| *percent == 100),
            "writer must forward core progress, got {seen:?}"
        );
    }
}
