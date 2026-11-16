//! Port of legacy tns_input.resolve_layout / extract_metadata and
//! core_engine.detect_statement_type, using umya-spreadsheet worksheets.

use crate::{normalize_header, row_type, TnsError};
use serde::Serialize;
use std::collections::HashSet;
use tns_excel::{Workbook, Worksheet};

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LayoutColumns {
    pub col_type: usize,
    pub col_point_num: usize,
    pub col_point_name: usize,
    pub col_meter_num: usize,
    pub col_zone: usize,
    pub col_sub_type: usize,
    pub col_read_start: usize,
    pub col_read_end: usize,
    pub col_diff: usize,
    pub col_coeff: usize,
    pub col_main_exp: usize,
    pub col_sub_deduct: usize,
    pub col_billed_vol: usize,
    pub first_data_row: usize,
    pub col_house_name: usize,
    pub col_total_label: usize,
}

impl Default for LayoutColumns {
    fn default() -> Self {
        Self {
            col_type: 1,
            col_point_num: 3,
            col_point_name: 4,
            col_meter_num: 5,
            col_zone: 9,
            col_sub_type: 10,
            col_read_start: 12,
            col_read_end: 13,
            col_diff: 15,
            col_coeff: 16,
            col_main_exp: 17,
            col_sub_deduct: 23,
            col_billed_vol: 28,
            first_data_row: 0,
            col_house_name: 0,
            col_total_label: 0,
        }
    }
}

impl LayoutColumns {
    fn shift(&mut self, shift: usize) {
        self.col_type += shift;
        self.col_point_num += shift;
        self.col_point_name += shift;
        self.col_meter_num += shift;
        self.col_zone += shift;
        self.col_sub_type += shift;
        self.col_read_start += shift;
        self.col_read_end += shift;
        self.col_diff += shift;
        self.col_coeff += shift;
        self.col_main_exp += shift;
        self.col_sub_deduct += shift;
        self.col_billed_vol += shift;
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Metadata {
    pub consumer: String,
    pub contract: String,
    pub period: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StatementKind {
    Dom,
    Gorod,
    Unknown,
}

impl StatementKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            StatementKind::Dom => "dom",
            StatementKind::Gorod => "gorod",
            StatementKind::Unknown => "unknown",
        }
    }
}

fn cell(sheet: &Worksheet, row: usize, column: usize) -> String {
    // umya-spreadsheet tuple coordinates are (column, row), unlike A1 strings.
    sheet.value((column as u32, row as u32))
}

/// Port of legacy tns_input.resolve_layout with the same error messages.
pub fn resolve_layout(sheet: &Worksheet) -> Result<LayoutColumns, TnsError> {
    let max_row = sheet.highest_row() as usize;
    let max_column = sheet.highest_column() as usize;
    let max_scan = max_row.min(250);
    let max_col = max_column.min(200);

    let mut candidates: Vec<(bool, usize, usize)> = Vec::new();
    for column in 1..=max_col {
        let mut codes = Vec::with_capacity(max_scan);
        for row in 1..=max_scan {
            codes.push(row_type(&cell(sheet, row, column)));
        }
        let has_type_header = (1..=max_scan.min(100))
            .any(|row| normalize_header(&cell(sheet, row, column)) == "тип");
        if codes.contains(&Some(100)) && (codes.contains(&Some(101)) || codes.contains(&Some(102))) {
            let count = codes
                .iter()
                .filter(|code| matches!(code, Some(100) | Some(101) | Some(102)))
                .count();
            candidates.push((has_type_header, count, column));
        }
    }

    candidates.sort_by(|left, right| right.cmp(left));
    if candidates.len() > 1
        && candidates[0].0 == candidates[1].0
        && candidates[0].1 == candidates[1].1
    {
        return Err(TnsError::Message(
            "Неоднозначная колонка типов строк. Проверьте заголовок «Тип».".into(),
        ));
    }

    let type_col = match candidates.first() {
        Some(candidate) => candidate.2,
        None => {
            let mut types: Vec<usize> = Vec::new();
            for column in 1..=max_col {
                if (1..=max_scan.min(100))
                    .any(|row| normalize_header(&cell(sheet, row, column)) == "тип")
                {
                    types.push(column);
                }
            }
            types.into_iter().min().unwrap_or(1)
        }
    };

    let first = (1..=max_row)
        .find(|row| row_type(&cell(sheet, *row, type_col)).is_some())
        .ok_or_else(|| {
            TnsError::Message(
                "Не найдены строки домов и приборов (типы 100/101/102). Выберите исходную ведомость ТНС."
                    .into(),
            )
        })?;

    let shift = type_col - 1;
    let mut columns = LayoutColumns::default();
    columns.shift(shift);

    let mut found: HashSet<&'static str> = HashSet::new();
    for row in 1..first {
        for column in 1..=max_column {
            let value = normalize_header(&cell(sheet, row, column));
            let key = if value.contains("начис") && value.contains("объем") {
                Some("col_billed_vol")
            } else if value.contains("зона") && value.contains("тариф") {
                Some("col_zone")
            } else if value.contains("завод") && value.contains("номер") {
                Some("col_meter_num")
            } else if value.contains("вычитан") && value.contains("суб") {
                Some("col_sub_deduct")
            } else if value.contains("суб") && value.contains("абонент") {
                Some("col_sub_type")
            } else if value.contains("разност") {
                Some("col_diff")
            } else if value.contains("коэф") {
                Some("col_coeff")
            } else if value.contains("основн") && value.contains("расход") {
                Some("col_main_exp")
            } else if value == "нач" || value == "начальныепоказания" {
                Some("col_read_start")
            } else if value == "кон" || value == "конечныепоказания" {
                Some("col_read_end")
            } else if value == "наименование" {
                Some("col_point_name")
            } else if value == "номер" {
                Some("col_point_num")
            } else {
                None
            };
            if let Some(key) = key {
                match key {
                    "col_billed_vol" => columns.col_billed_vol = column,
                    "col_zone" => columns.col_zone = column,
                    "col_meter_num" => columns.col_meter_num = column,
                    "col_sub_deduct" => columns.col_sub_deduct = column,
                    "col_sub_type" => columns.col_sub_type = column,
                    "col_diff" => columns.col_diff = column,
                    "col_coeff" => columns.col_coeff = column,
                    "col_main_exp" => columns.col_main_exp = column,
                    "col_read_start" => columns.col_read_start = column,
                    "col_read_end" => columns.col_read_end = column,
                    "col_point_name" => columns.col_point_name = column,
                    "col_point_num" => columns.col_point_num = column,
                    _ => {}
                }
                found.insert(key);
            }
        }
    }

    if !found.contains("col_billed_vol")
        && !(found.is_empty() && type_col == 1 && (max_column == 28 || max_column == 29))
    {
        return Err(TnsError::Message(
            "Не найдена колонка «Начисленный объем». Нельзя безопасно выбрать расход по номеру столбца."
                .into(),
        ));
    }
    if !found.contains("col_zone") && !found.is_empty() {
        return Err(TnsError::Message(
            "Не найдена колонка «Зона тарифа». Проверьте исходную ведомость.".into(),
        ));
    }

    columns.first_data_row = first;
    columns.col_house_name = columns.col_point_num;
    columns.col_total_label = (type_col + 1).max(columns.col_point_num.saturating_sub(1));
    Ok(columns)
}

fn extract_period(value: &str) -> Option<String> {
    let lower = value.to_lowercase();
    let months = [
        "январ", "феврал", "март", "апрел", "ма", "июн", "июл", "август", "сентябр",
        "октябр", "ноябр", "декабр",
    ];
    let start = months.iter().filter_map(|month| lower.find(month)).min()?;
    let tail = &lower[start..];
    let relative_year = tail.find("20")?;
    let year_start = start + relative_year;
    let year_end = year_start + 4;
    if year_end > value.len() {
        return None;
    }
    let year = &value[year_start..year_end];
    if year.len() == 4 && year.chars().all(|character| character.is_ascii_digit()) {
        Some(value[start..year_end].trim().to_string())
    } else {
        None
    }
}

/// Port of legacy tns_input.extract_metadata.
pub fn extract_metadata(sheet: &Worksheet) -> Metadata {
    let max_row = (sheet.highest_row() as usize).min(30);
    let max_column = (sheet.highest_column() as usize).min(100);
    let mut strings = Vec::new();
    for row in 1..=max_row {
        for column in 1..=max_column {
            let value = cell(sheet, row, column);
            if !value.is_empty() {
                strings.push(value);
            }
        }
    }

    let contract = strings
        .iter()
        .find(|value| value.contains("23110604327") || value.contains("23110603789"))
        .cloned()
        .unwrap_or_default();
    let consumer = strings
        .iter()
        .find(|value| {
            let normalized = normalize_header(value);
            normalized.contains("южныйгород") || normalized.contains("южныйдом")
        })
        .cloned()
        .unwrap_or_default();
    let period = strings
        .iter()
        .find_map(|value| extract_period(value))
        .unwrap_or_default();

    Metadata {
        consumer,
        contract,
        period,
    }
}

/// Port of legacy core_engine.detect_statement_type (without the sha256 cache).
pub fn detect_statement_type(book: &Workbook) -> (StatementKind, String, String) {
    let sheet = match book.sheet(0) {
        Ok(sheet) => sheet,
        Err(_) => return (StatementKind::Unknown, String::new(), String::new()),
    };
    let metadata = extract_metadata(sheet);
    let consumer = metadata.consumer.to_lowercase();
    if consumer.contains("город") || metadata.contract.contains("23110604327") {
        (
            StatementKind::Gorod,
            "ООО \"Южный город\"".to_string(),
            "23110604327".to_string(),
        )
    } else if consumer.contains("дом") || metadata.contract.contains("23110603789") {
        (
            StatementKind::Dom,
            "ООО \"Южный Дом\"".to_string(),
            "23110603789".to_string(),
        )
    } else {
        (StatementKind::Unknown, metadata.consumer, metadata.contract)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::{Path, PathBuf};

    fn fixture(name: &str) -> Workbook {
        let path: PathBuf = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("tests")
            .join("parity")
            .join("fixtures")
            .join(name);
        tns_excel::read(path).expect("read fixture")
    }

    #[test]
    fn resolves_dom_layout() {
        let book = fixture("dom_april_2026.xlsx");
        let sheet = book.sheet(0).expect("sheet");
        let columns = resolve_layout(sheet).expect("layout");
        assert_eq!(columns.col_type, 1);
        assert_eq!(columns.col_point_num, 3);
        assert_eq!(columns.col_billed_vol, 28);
        assert_eq!(columns.first_data_row, 9);
    }

    #[test]
    fn extracts_metadata() {
        let book = fixture("gorod_april_2026.xlsx");
        let sheet = book.sheet(0).expect("sheet");
        let metadata = extract_metadata(sheet);
        assert!(metadata.consumer.contains("Южный Город"));
        assert!(metadata.contract.contains("23110604327"));
        assert_eq!(metadata.period, "Апрель 2026");
    }

    #[test]
    fn detects_statement_kinds() {
        let dom = fixture("dom_april_2026.xlsx");
        let (kind, _, _) = detect_statement_type(&dom);
        assert_eq!(kind, StatementKind::Dom);
        let gorod = fixture("gorod_april_2026.xlsx");
        let (kind, _, _) = detect_statement_type(&gorod);
        assert_eq!(kind, StatementKind::Gorod);
    }

    #[test]
    fn empty_sheet_is_rejected() {
        let book = tns_excel::new_file();
        let sheet = book.sheet(0).expect("sheet");
        assert!(resolve_layout(sheet).is_err());
    }
}
