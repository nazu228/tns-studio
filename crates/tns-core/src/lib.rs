//! Pure TNS statement parsing and calculation logic.
//!
//! This is a Rust port of the pure parts of legacy/pyqt/tns_input.py and
//! legacy/pyqt/core_engine.py. The legacy Python engine remains the oracle;
//! tests/parity contains golden fixtures and screenshots.

use std::fmt;

pub mod layout;
pub mod output;
pub mod process;
pub use layout::*;
pub use process::*;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Zone {
    Day,
    Night,
    Odn,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TnsError {
    InvalidNumber { coordinate: String, value: String },
    NonFinite { coordinate: String },
    Message(String),
}

impl fmt::Display for TnsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TnsError::InvalidNumber { coordinate, value } => {
                write!(f, "В ячейке {} некорректный расход: '{}'.", coordinate, value)
            }
            TnsError::NonFinite { coordinate } => {
                write!(f, "В ячейке {} расход не является конечным числом.", coordinate)
            }
            TnsError::Message(message) => write!(f, "{}", message),
        }
    }
}

impl std::error::Error for TnsError {}

fn is_word_char(c: char) -> bool {
    c.is_ascii_alphanumeric() || ('а'..='я').contains(&c)
}

/// Port of legacy tns_input.normalize_header.
///
/// Lowercase, ё→е, drop `_x000d_`, remove a hyphen (and following spaces) only
/// when it sits between word characters, then keep Latin/Cyrillic letters and
/// digits. This mirrors the legacy regex `[^a-zа-я0-9]+`.
pub fn normalize_header(value: &str) -> String {
    let lower = value.to_lowercase().replace('ё', "е").replace("_x000d_", " ");
    let chars: Vec<char> = lower.chars().collect();
    let mut out = String::with_capacity(chars.len());
    let mut index = 0;
    while index < chars.len() {
        let current = chars[index];
        if current == '-' {
            let previous_is_word = out.chars().last().map(is_word_char).unwrap_or(false);
            let mut next_index = index + 1;
            while next_index < chars.len() && chars[next_index].is_whitespace() {
                next_index += 1;
            }
            let next_is_word = chars.get(next_index).copied().map(is_word_char).unwrap_or(false);
            if previous_is_word && next_is_word {
                index = next_index;
                continue;
            }
        }
        if is_word_char(current) {
            out.push(current);
        }
        index += 1;
    }
    out
}

/// Port of legacy tns_input.row_type: only 100/101/102 are meaningful.
pub fn row_type(value: &str) -> Option<u8> {
    let number: f64 = value.trim().replace(',', ".").parse().ok()?;
    if number == 100.0 || number == 101.0 || number == 102.0 {
        Some(number as u8)
    } else {
        None
    }
}

/// Excel column letter for a 1-based column number (1 -> A, 28 -> AB).
pub(crate) fn column_letter(mut column: usize) -> String {
    let mut result = String::new();
    while column > 0 {
        let remainder = (column - 1) % 26;
        result.insert(0, (b'A' + remainder as u8) as char);
        column = (column - 1) / 26;
    }
    result
}

/// Port of legacy core_engine.safe_float: never panics, returns default on junk.
pub fn safe_float(value: Option<&str>, default: f64) -> f64 {
    let Some(raw) = value else {
        return default;
    };
    let normalized = raw
        .trim()
        .replace('\u{a0}', "")
        .replace(' ', "")
        .replace(',', ".");
    if normalized.is_empty() {
        return default;
    }
    let lowered = normalized.to_ascii_lowercase();
    if matches!(lowered.as_str(), "-" | "—" | "none" | "null" | "nan") {
        return default;
    }
    normalized.parse::<f64>().unwrap_or(default)
}

/// Port of legacy tns_input.numeric_value, including its exact Russian errors.
pub fn numeric_value(value: Option<&str>, coordinate: &str) -> Result<f64, TnsError> {
    let Some(raw) = value else {
        return Ok(0.0);
    };
    let trimmed = raw.trim();
    if trimmed.is_empty() || trimmed == "-" || trimmed == "—" {
        return Ok(0.0);
    }
    let normalized = trimmed
        .replace('\u{a0}', "")
        .replace(' ', "")
        .replace(',', ".");
    match normalized.parse::<f64>() {
        Ok(number) if number.is_finite() => Ok(number),
        Ok(_) => Err(TnsError::NonFinite {
            coordinate: coordinate.to_string(),
        }),
        Err(_) => Err(TnsError::InvalidNumber {
            coordinate: coordinate.to_string(),
            value: raw.to_string(),
        }),
    }
}

/// Port of legacy core_engine.classify_zone.
///
/// ODN is checked first, then night, then day; anything unknown is ODN.
/// Latin t/c are folded to Cyrillic т/с like the legacy code.
pub fn classify_zone(zone: &str) -> Zone {
    let normalized = zone
        .to_lowercase()
        .replace('\u{a0}', " ")
        .replace('t', "т")
        .replace('c', "с");
    if normalized.is_empty() {
        return Zone::Odn;
    }
    if ["одн", "общедомовые", "место общего пользования", "без дифференциации"]
        .iter()
        .any(|word| normalized.contains(word))
    {
        return Zone::Odn;
    }
    if ["ночь", "ноч", "т2", "т-2"]
        .iter()
        .any(|word| normalized.contains(word))
    {
        return Zone::Night;
    }
    if ["день", "дн", "пик", "полупик", "т1", "т-1"]
        .iter()
        .any(|word| normalized.contains(word))
    {
        return Zone::Day;
    }
    Zone::Odn
}

/// Port of legacy tns_input.total_row over a slice of label cells.
pub fn total_row(values: &[&str]) -> bool {
    values.iter().any(|value| {
        let normalized = normalize_header(value);
        normalized.starts_with("итого") || normalized.starts_with("всего")
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_russian_headers() {
        assert_eq!(normalize_header("Начисленный объём"), "начисленныйобъем");
        assert_eq!(normalize_header("Зона тарифа"), "зонатарифа");
        assert_eq!(normalize_header("Суб. абонент"), "субабонент");
        assert_eq!(normalize_header("T-1"), "t1");
        assert_eq!(normalize_header("  Тип  "), "тип");
    }

    #[test]
    fn recognizes_row_types() {
        assert_eq!(row_type("100"), Some(100));
        assert_eq!(row_type("101.0"), Some(101));
        assert_eq!(row_type(" 102 "), Some(102));
        assert_eq!(row_type("99"), None);
        assert_eq!(row_type("abc"), None);
    }

    #[test]
    fn safe_float_never_panics() {
        assert_eq!(safe_float(Some("1 000,00"), 0.0), 1000.0);
        assert_eq!(safe_float(Some("—"), 7.0), 7.0);
        assert_eq!(safe_float(Some("none"), 7.0), 7.0);
        assert_eq!(safe_float(None, 7.0), 7.0);
        assert_eq!(safe_float(Some("junk"), 3.5), 3.5);
    }

    #[test]
    fn numeric_value_matches_legacy_contract() {
        assert_eq!(numeric_value(Some("1 000,00"), "AB11"), Ok(1000.0));
        assert_eq!(numeric_value(Some("—"), "AB11"), Ok(0.0));
        assert_eq!(numeric_value(None, "AB11"), Ok(0.0));
        assert!(numeric_value(Some("abc"), "AB11").is_err());
    }

    #[test]
    fn classifies_zones() {
        assert_eq!(classify_zone("День"), Zone::Day);
        assert_eq!(classify_zone("Т1"), Zone::Day);
        assert_eq!(classify_zone("Пик"), Zone::Day);
        assert_eq!(classify_zone("Ночь"), Zone::Night);
        assert_eq!(classify_zone("Т2"), Zone::Night);
        assert_eq!(classify_zone("ОДН"), Zone::Odn);
        assert_eq!(classify_zone(""), Zone::Odn);
        assert_eq!(classify_zone("Одноставочный"), Zone::Odn);
    }

    #[test]
    fn detects_total_rows() {
        assert!(total_row(&["Итого:", "", ""]));
        assert!(total_row(&["", "Всего", ""]));
        assert!(!total_row(&["", "Дом 1", ""]));
    }
}
