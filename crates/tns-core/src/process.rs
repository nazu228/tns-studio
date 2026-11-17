//! Port of legacy core_engine.process_statement.
//!
//! Reproduces the legacy parsing, validation, totals, preview rows,
//! period/paths, progress events and output workbook layout (values, formulas,
//! merges, freeze panes, dimensions). Styles/CF/hyperlinks are slice 2. The
//! golden result JSON and the openpyxl xlsx signature are the oracles.

use crate::output;
use crate::{
    classify_zone, column_letter, detect_statement_type, extract_metadata, numeric_value,
    resolve_layout, row_type, total_row, LayoutColumns, StatementKind, TnsError, Zone,
};
use serde::Serialize;
use std::path::{Path, PathBuf};
use tns_excel::{read, Worksheet};

#[derive(Debug, Clone, Serialize)]
pub struct PreviewRow {
    pub num: usize,
    pub name: String,
    pub day: f64,
    pub night: f64,
    pub odn: f64,
    pub simple: f64,
    pub total: f64,
    pub control: f64,
    pub diff: f64,
    pub meters: String,
    pub meters_active: usize,
    pub meters_res: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct ProcessResult {
    pub success: bool,
    pub consumer: String,
    pub contract: String,
    pub period: String,
    pub subfolder_name: String,
    pub target_dir: String,
    pub target_path: String,
    pub warning: Option<String>,
    pub houses_count: usize,
    pub total_day: f64,
    pub total_night: f64,
    pub total_odn: f64,
    pub total_simple: f64,
    pub total_all: f64,
    pub statement_total: f64,
    pub balance_diff: f64,
    pub balance_ok: bool,
    pub preview_rows: Vec<PreviewRow>,
    pub columns_used: LayoutColumns,
}

pub struct ProcessOptions<'a> {
    pub output_dir: Option<PathBuf>,
    pub custom_filename: Option<String>,
    pub month: Option<String>,
    pub year: Option<String>,
    pub progress: Option<&'a dyn Fn(u8, &str)>,
    pub cancel: Option<&'a dyn Fn() -> bool>,
}

impl<'a> Default for ProcessOptions<'a> {
    fn default() -> Self {
        Self {
            output_dir: None,
            custom_filename: None,
            month: None,
            year: None,
            progress: None,
            cancel: None,
        }
    }
}

#[derive(Debug)]
pub(crate) struct House {
    pub(crate) header_row: usize,
    pub(crate) name: String,
    pub(crate) day_rows: Vec<usize>,
    pub(crate) night_rows: Vec<usize>,
    pub(crate) odn_rows: Vec<usize>,
    pub(crate) sub_rows: Vec<usize>,
}

impl House {
    pub(crate) fn all_meter_rows(&self) -> Vec<usize> {
        let mut rows = Vec::with_capacity(self.day_rows.len() + self.night_rows.len() + self.odn_rows.len());
        rows.extend(&self.day_rows);
        rows.extend(&self.night_rows);
        rows.extend(&self.odn_rows);
        rows
    }
}

fn cell(sheet: &Worksheet, row: usize, column: usize) -> String {
    // umya tuple coordinates are (column, row), unlike A1 strings.
    sheet.value((column as u32, row as u32))
}

fn round3(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}

fn emit(progress: Option<&dyn Fn(u8, &str)>, percent: u8, message: &str) {
    if let Some(callback) = progress {
        callback(percent, message);
    }
}

fn check_cancel(cancel: Option<&dyn Fn() -> bool>) -> Result<(), TnsError> {
    if cancel.map(|callback| callback()).unwrap_or(false) {
        Err(TnsError::Message("Расчет отменен пользователем.".into()))
    } else {
        Ok(())
    }
}

pub(crate) fn billed_value(sheet: &Worksheet, row: usize, column: usize) -> Result<f64, TnsError> {
    let coordinate = format!("{}{}", column_letter(column), row);
    let Some(cell) = sheet.cell((column as u32, row as u32)) else {
        return Ok(0.0);
    };
    if cell.is_formula() {
        return cell.value_number().ok_or_else(|| {
            TnsError::Message(format!(
                "Формула в {} не пересчитана. Откройте исходный файл в Excel, пересчитайте и сохраните его.",
                coordinate
            ))
        });
    }
    let value = cell.value();
    numeric_value(Some(value.as_ref()), &coordinate)
}

fn is_total_row(sheet: &Worksheet, row: usize, columns: &LayoutColumns) -> bool {
    let mut values = Vec::new();
    for column in (columns.col_type + 1)..=columns.col_point_name {
        values.push(cell(sheet, row, column));
    }
    let refs: Vec<&str> = values.iter().map(String::as_str).collect();
    total_row(&refs)
}

fn sum_rows(sheet: &Worksheet, rows: &[usize], column: usize) -> Result<f64, TnsError> {
    let mut total = 0.0;
    for row in rows {
        total += billed_value(sheet, *row, column)?;
    }
    Ok(total)
}

/// Parse, validate, compute the result and write the output workbook layout.
pub fn process_statement(
    source: &Path,
    options: ProcessOptions<'_>,
) -> Result<ProcessResult, TnsError> {
    let source_name = source
        .file_name()
        .map(|value| value.to_string_lossy().to_string())
        .unwrap_or_else(|| "файл".into());
    emit(options.progress, 5, &format!("Чтение файла: {}...", source_name));
    check_cancel(options.cancel)?;

    let mut book = read(source).map_err(|error| TnsError::Message(error.to_string()))?;
    let sheet = book
        .sheet(0)
        .map_err(|error| TnsError::Message(format!("Не удалось открыть лист: {}", error)))?;
    let columns = resolve_layout(sheet)?;
    let metadata = extract_metadata(sheet);
    let (kind, consumer, contract) = detect_statement_type(&book);

    let (period, period_slug, subfolder_name) = match (options.month.as_deref(), options.year.as_deref()) {
        (Some(month), Some(year)) => (
            format!("{} {} г.", month, year),
            format!("{}_{}", month, year),
            format!("{} {} ТНС", month, year),
        ),
        _ if !metadata.period.is_empty() => {
            let clean = metadata.period.replace("г.", "").trim().to_string();
            (
                metadata.period.clone(),
                clean.replace(' ', "_"),
                format!("{} ТНС", clean),
            )
        }
        _ => (
            "Август 2026 г.".into(),
            "Август_2026".into(),
            "Август 2026 ТНС".into(),
        ),
    };

    let output_dir = options
        .output_dir
        .clone()
        .unwrap_or_else(|| source.parent().unwrap_or_else(|| Path::new(".")).to_path_buf());
    let same_folder = output_dir
        .file_name()
        .map(|name| name.to_string_lossy().to_lowercase() == subfolder_name.to_lowercase())
        .unwrap_or(false);
    let target_dir = if same_folder {
        output_dir
    } else {
        output_dir.join(&subfolder_name)
    };

    let prefix = if kind == StatementKind::Gorod { "Город" } else { "Дом" };
    let filename = match options.custom_filename {
        Some(custom) if custom.ends_with(".xlsx") => custom,
        Some(custom) => format!("{}.xlsx", custom),
        None => format!("{}_{}.xlsx", prefix, period_slug),
    };
    let target_path = target_dir.join(&filename);

    emit(options.progress, 15, "Анализ структуры столбцов и приборов учета...");

    let max_row = sheet.highest_row() as usize;
    let mut houses: Vec<House> = Vec::new();
    let mut current: Option<usize> = None;
    let mut statement_total_row: Option<usize> = None;

    for row in columns.first_data_row..=max_row {
        check_cancel(options.cancel)?;
        match row_type(&cell(sheet, row, columns.col_type)) {
            Some(100) => {
                if is_total_row(sheet, row, &columns) {
                    statement_total_row = Some(row);
                    break;
                }
                houses.push(House {
                    header_row: row,
                    name: cell(sheet, row, columns.col_house_name),
                    day_rows: Vec::new(),
                    night_rows: Vec::new(),
                    odn_rows: Vec::new(),
                    sub_rows: Vec::new(),
                });
                current = Some(houses.len() - 1);
            }
            Some(101) => {
                if let Some(index) = current {
                    match classify_zone(&cell(sheet, row, columns.col_zone)) {
                        Zone::Day => houses[index].day_rows.push(row),
                        Zone::Night => houses[index].night_rows.push(row),
                        Zone::Odn => houses[index].odn_rows.push(row),
                    }
                }
            }
            Some(102) => {
                if let Some(index) = current {
                    houses[index].sub_rows.push(row);
                }
            }
            _ => {}
        }
    }

    if houses.is_empty() {
        return Err(TnsError::Message(
            "Не найдены дома в исходной ведомости. Проверьте типы строк и структуру таблицы.".into(),
        ));
    }
    let statement_total_row = statement_total_row.ok_or_else(|| {
        TnsError::Message(
            "Не найдена итоговая строка ведомости «Итого». Расчет остановлен, чтобы не создать циклические формулы."
                .into(),
        )
    })?;

    for house in &houses {
        billed_value(sheet, house.header_row, columns.col_billed_vol)?;
        for row in house.all_meter_rows() {
            billed_value(sheet, row, columns.col_billed_vol)?;
        }
    }
    let statement_total = billed_value(sheet, statement_total_row, columns.col_billed_vol)?;

    let mut preview_rows = Vec::with_capacity(houses.len());
    let mut total_day = 0.0;
    let mut total_night = 0.0;
    let mut total_odn = 0.0;

    for (index, house) in houses.iter().enumerate() {
        let day = sum_rows(sheet, &house.day_rows, columns.col_billed_vol)?;
        let night = sum_rows(sheet, &house.night_rows, columns.col_billed_vol)?;
        let odn = sum_rows(sheet, &house.odn_rows, columns.col_billed_vol)?;
        let total = day + night + odn;
        let control = billed_value(sheet, house.header_row, columns.col_billed_vol)?;
        let diff = round3(total - control);
        let all_meters = house.all_meter_rows();
        let mut reserve = 0;
        for row in &all_meters {
            if billed_value(sheet, *row, columns.col_billed_vol)? == 0.0 {
                reserve += 1;
            }
        }
        let active = all_meters.len() - reserve;
        preview_rows.push(PreviewRow {
            num: index + 1,
            name: house.name.clone(),
            day,
            night,
            odn,
            simple: odn,
            total,
            control,
            diff,
            meters: format!("{} раб. / {} рез.", active, reserve),
            meters_active: active,
            meters_res: reserve,
        });
        total_day += day;
        total_night += night;
        total_odn += odn;
    }

    let total_all = total_day + total_night + total_odn;
    let balance_diff = round3(total_all - statement_total);
    let balance_ok = balance_diff == 0.0;

    emit(
        options.progress,
        35,
        &format!(
            "Найдено домов: {}. Разметка и добавление формул в Ведомость ЭП...",
            houses.len()
        ),
    );
    let layout = output::write_statement(&mut book, &columns, &houses, statement_total_row)?;

    emit(
        options.progress,
        65,
        "Построение листа «Сводка по домам» (Дашборд)...",
    );
    output::write_summary(
        &mut book,
        &columns,
        &layout,
        &houses,
        statement_total_row,
        &consumer,
        &contract,
        &period,
    )?;

    emit(
        options.progress,
        90,
        &format!("Сохранение файла в папку {}...", subfolder_name),
    );
    // Legacy creates the summary total cell A from an empty string, which
    // openpyxl writes as t="inlineStr"; umya needs the attribute patched in.
    let empty_inline = [(0usize, format!("A{}", 6 + houses.len()))];
    let (saved_path, warning) =
        tns_excel::safe_save_with_empty_inline(&book, &target_path, &empty_inline)
            .map_err(|error| TnsError::Message(error.to_string()))?;

    emit(
        options.progress,
        100,
        &format!("Готово! Сохранен в: {}", subfolder_name),
    );

    Ok(ProcessResult {
        success: true,
        consumer,
        contract,
        period,
        subfolder_name,
        target_dir: target_dir.to_string_lossy().to_string(),
        target_path: saved_path.to_string_lossy().to_string(),
        warning,
        houses_count: houses.len(),
        total_day,
        total_night,
        total_odn,
        total_simple: total_odn,
        total_all,
        statement_total,
        balance_diff,
        balance_ok,
        preview_rows,
        columns_used: columns,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;
    use std::path::{Path, PathBuf};
    use tns_excel::{
        ConditionalFormatValues, ConditionalFormattingOperatorValues, HorizontalAlignmentValues,
        Style, VerticalAlignmentValues,
    };

    fn fill_rgb(style: &Style) -> Option<String> {
        style
            .fill()?
            .pattern_fill()?
            .foreground_color()
            .map(|color| color.argb_str())
    }

    fn fixture(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("tests")
            .join("parity")
            .join("fixtures")
            .join(name)
    }

    fn golden(name: &str) -> Value {
        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("tests")
            .join("parity")
            .join("fixtures")
            .join("golden")
            .join(name);
        serde_json::from_str(&std::fs::read_to_string(path).expect("golden")).expect("json")
    }

    fn assert_number(left: &Value, right: &Value, field: &str) {
        let left = left.as_f64().unwrap_or_else(|| panic!("{}: left is not a number", field));
        let right = right.as_f64().unwrap_or_else(|| panic!("{}: right is not a number", field));
        assert!((left - right).abs() < 1e-9, "{}: {} != {}", field, left, right);
    }

    fn assert_preview_rows(actual: &Value, expected: &Value) {
        let actual = actual.as_array().expect("actual rows");
        let expected = expected.as_array().expect("expected rows");
        assert_eq!(actual.len(), expected.len());
        for (index, (left, right)) in actual.iter().zip(expected).enumerate() {
            assert_eq!(left["num"], right["num"], "row {} num", index);
            assert_eq!(left["name"], right["name"], "row {} name", index);
            assert_eq!(left["meters"], right["meters"], "row {} meters", index);
            assert_eq!(left["meters_active"], right["meters_active"], "row {} active", index);
            assert_eq!(left["meters_res"], right["meters_res"], "row {} reserve", index);
            for field in ["day", "night", "odn", "simple", "total", "control", "diff"] {
                assert_number(&left[field], &right[field], &format!("row {} {}", index, field));
            }
        }
    }

    #[test]
    fn result_matches_dom_golden() {
        let dir = tempfile::tempdir().expect("tempdir");
        let result = process_statement(
            &fixture("dom_april_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(dir.path().to_path_buf()),
                month: Some("Апрель".into()),
                year: Some("2026".into()),
                ..Default::default()
            },
        )
        .expect("process");
        let actual = serde_json::to_value(&result).expect("serialize");
        let expected = golden("dom_april_2026.json")["result"].clone();

        for key in [
            "success",
            "consumer",
            "contract",
            "period",
            "subfolder_name",
            "houses_count",
            "total_day",
            "total_night",
            "total_odn",
            "total_simple",
            "total_all",
            "statement_total",
            "balance_diff",
            "balance_ok",
            "columns_used",
        ] {
            assert_eq!(actual[key], expected[key], "field {}", key);
        }
        assert_preview_rows(&actual["preview_rows"], &expected["preview_rows"]);
        assert_eq!(
            Path::new(result.target_path.as_str())
                .file_name()
                .unwrap()
                .to_string_lossy(),
            "Дом_Апрель_2026.xlsx"
        );
    }

    #[test]
    fn result_matches_gorod_golden() {
        let dir = tempfile::tempdir().expect("tempdir");
        let result = process_statement(
            &fixture("gorod_april_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(dir.path().to_path_buf()),
                month: Some("Апрель".into()),
                year: Some("2026".into()),
                ..Default::default()
            },
        )
        .expect("process");
        let actual = serde_json::to_value(&result).expect("serialize");
        let expected = golden("gorod_april_2026.json")["result"].clone();
        assert_eq!(actual["consumer"], expected["consumer"]);
        assert_eq!(actual["houses_count"], expected["houses_count"]);
        assert_number(&actual["total_all"], &expected["total_all"], "total_all");
        assert_preview_rows(&actual["preview_rows"], &expected["preview_rows"]);
    }

    #[test]
    fn cancellation_has_legacy_message() {
        let error = process_statement(
            &fixture("dom_april_2026.xlsx"),
            ProcessOptions {
                cancel: Some(&|| true),
                ..Default::default()
            },
        )
        .expect_err("must cancel");
        assert_eq!(error.to_string(), "Расчет отменен пользователем.");
    }

    #[test]
    fn writes_output_workbook_layout() {
        let dir = tempfile::tempdir().expect("tempdir");
        let result = process_statement(
            &fixture("dom_april_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(dir.path().to_path_buf()),
                month: Some("Апрель".into()),
                year: Some("2026".into()),
                ..Default::default()
            },
        )
        .expect("process");

        assert!(Path::new(&result.target_path).is_file());
        assert!(result.warning.is_none());

        let mut book = tns_excel::read(&result.target_path).expect("read output");
        assert_eq!(book.sheet_count(), 2);
        assert_eq!(book.sheet(0).expect("summary").name(), "Сводка по домам");
        assert_eq!(book.sheet(1).expect("statement").name(), "Ведомость ЭП");

        {
            let summary = book.sheet_mut(0).expect("summary");
            assert_eq!(summary.merge_cells().len(), 3);
            assert_eq!(summary.column_dimension("A").expect("A").width(), 6.0);
            assert_eq!(summary.row_dimension(1).expect("row 1").height(), 24.0);
            assert_eq!(
                summary.cell((2, 6)).expect("B6").formula(),
                "'Ведомость ЭП'!C9"
            );
            let pane = summary
                .sheet_views_mut()
                .sheet_view_list()
                .first()
                .and_then(|view| view.pane())
                .expect("freeze pane");
            assert_eq!(pane.top_left_cell().get_coordinate(), "C6");
        }

        {
            let statement = book.sheet_mut(1).expect("statement");
            assert_eq!(
                statement.cell((32, 9)).expect("AF9").formula(),
                "SUM(AB10, AB11, AB12)"
            );
            assert_eq!(
                statement.cell((38, 9)).expect("AL9").formula(),
                "IF(AK9=0, \"✔ Сошлось\", \"❌ Ошибка\")"
            );
            assert_eq!(
                statement.column_dimension("AD").expect("AD").width(),
                24.0
            );
        }
    }

    #[test]
    fn custom_filename_is_applied() {
        let dir = tempfile::tempdir().expect("tempdir");
        let result = process_statement(
            &fixture("dom_march_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(dir.path().to_path_buf()),
                custom_filename: Some("custom".into()),
                month: Some("Март".into()),
                year: Some("2026".into()),
                ..Default::default()
            },
        )
        .expect("process");
        assert!(result.target_path.ends_with("custom.xlsx"));
    }

    #[test]
    fn writes_legacy_styles_links_and_formatting() {
        let dir = tempfile::tempdir().expect("tempdir");
        let result = process_statement(
            &fixture("dom_april_2026.xlsx"),
            ProcessOptions {
                output_dir: Some(dir.path().to_path_buf()),
                month: Some("Апрель".into()),
                year: Some("2026".into()),
                ..Default::default()
            },
        )
        .expect("process");
        let book = tns_excel::read(&result.target_path).expect("read output");

        {
            let statement = book.sheet(1).expect("statement");
            let ad10 = statement.cell("AD10").expect("AD10");
            let style = ad10.style();
            assert_eq!(style.font().map(|font| font.name()), Some("Segoe UI"));
            assert_eq!(style.font().map(|font| font.size()), Some(9.0));
            assert_eq!(style.font().map(|font| font.bold()), Some(true));
            assert!(fill_rgb(style).is_some_and(|rgb| rgb.ends_with("FFF2CC")));
            let alignment = style.alignment().expect("AD10 alignment");
            assert_eq!(*alignment.horizontal(), HorizontalAlignmentValues::Center);
            assert_eq!(*alignment.vertical(), VerticalAlignmentValues::Center);
            assert!(alignment.wrap_text());

            let ae10 = statement.cell("AE10").expect("AE10");
            assert_eq!(ae10.value().as_ref(), "В работе (с расходом)");
            assert!(fill_rgb(ae10.style()).is_some_and(|rgb| rgb.ends_with("1F4E79")));
            assert_eq!(ae10.style().font().map(|font| font.bold()), Some(true));
            let alignment = ae10.style().alignment().expect("AE10 alignment");
            assert_eq!(*alignment.horizontal(), HorizontalAlignmentValues::Center);
            assert!(alignment.wrap_text());
        }

        let summary = book.sheet(0).expect("summary");

        let link = summary.cell("B6").expect("B6").hyperlink().expect("link");
        assert_eq!(link.url(), "#'Ведомость ЭП'!AF9");
        assert!(!link.location());
        assert!(link.tooltip().is_empty());
        assert_eq!(
            summary.cell("B7").expect("B7").hyperlink().expect("link").url(),
            "#'Ведомость ЭП'!AF15"
        );

        let formats = summary.conditional_formatting_collection();
        assert_eq!(formats.len(), 1);
        assert_eq!(formats[0].sequence_of_references().get_sqref(), "H6:H8");
        let rules = formats[0].conditional_collection();
        assert_eq!(rules.len(), 2);
        assert_eq!(*rules[0].get_type(), ConditionalFormatValues::CellIs);
        assert_eq!(
            *rules[0].operator(),
            ConditionalFormattingOperatorValues::Equal
        );
        assert_eq!(rules[0].priority(), 1);
        assert!(rules[0].stop_if_true());
        assert_eq!(
            *rules[1].operator(),
            ConditionalFormattingOperatorValues::NotEqual
        );
        assert_eq!(rules[1].priority(), 2);
        assert!(rules[1].stop_if_true());

        let total_row = 6 + result.houses_count;
        for column in ["A", "I", "J"] {
            let coordinate = format!("{}{}", column, total_row);
            let cell = summary
                .cell(coordinate.as_str())
                .unwrap_or_else(|| panic!("missing total cell {}", coordinate));
            assert_eq!(cell.value().as_ref(), "");
            assert!(fill_rgb(cell.style()).is_some_and(|rgb| rgb.ends_with("D9E1F2")));
            assert_eq!(cell.style().font().map(|font| font.bold()), Some(true));
            assert_eq!(cell.style().font().map(|font| font.size()), Some(10.0));
        }

        // Legacy leaves C/D/E/G at the workbook default font (Calibri 11).
        for coordinate in ["C6", "G6"] {
            let font = summary
                .cell(coordinate)
                .expect(coordinate)
                .style()
                .font()
                .expect("font");
            assert_eq!(font.name(), "Calibri");
            assert_eq!(font.size(), 11.0);
        }
        let h6 = summary
            .cell("H6")
            .expect("H6")
            .style()
            .font()
            .expect("font");
        assert_eq!(h6.name(), "Segoe UI");
        assert_eq!(h6.size(), 10.0);
        assert!(h6.bold());
    }
}
