//! Text normalisation, cell-number parsing and zone classification.

/// Collapse any run of whitespace (including NBSP and line breaks) to one
/// space and trim the result.
pub fn normalize_text(value: &str) -> String {
    let mut output = String::with_capacity(value.len());
    let mut pending_space = false;
    for character in value.chars() {
        if character == '\u{0}' {
            pending_space = !output.is_empty();
        } else if character.is_whitespace() || character == '\u{00a0}' {
            pending_space = !output.is_empty();
        } else {
            if pending_space {
                output.push(' ');
                pending_space = false;
            }
            output.push(character);
        }
    }
    output
}

/// Remove every whitespace character, including NBSP.
pub fn strip_whitespace(value: &str) -> String {
    value
        .chars()
        .filter(|character| !character.is_whitespace() && *character != '\u{00a0}')
        .collect()
}

/// Parse one cell number. Accepts NBSP/space thousands separators, a decimal
/// comma, all dash-like minus signs, and treats empty values as `None`.
pub fn parse_number(value: &str) -> Option<f64> {
    let mut cleaned = String::with_capacity(value.len());
    for character in value.chars() {
        match character {
            '\u{00a0}' | '\u{2009}' | '\u{202f}' | ' ' | '\t' | '\r' | '\n' => {}
            ',' => cleaned.push('.'),
            '\u{2212}' | '\u{2010}' | '\u{2011}' | '\u{2012}' | '\u{2013}' | '\u{2014}'
            | '\u{2015}' | '\u{FE63}' => cleaned.push('-'),
            _ => cleaned.push(character),
        }
    }
    if cleaned.is_empty()
        || cleaned == "-"
        || cleaned == "."
        || cleaned == ".."
        || cleaned == "-."
    {
        return None;
    }
    cleaned.parse::<f64>().ok()
}

/// Find every number in a free-form row such as `Итого: 1 032 745,77 5 419 801,94`.
///
/// A single space is kept inside a number only when it is followed by exactly
/// three digits and then a non-digit (a thousands group). This is what splits
/// the glued total layout `223 073,372 1 159 713,33` back into two numbers.
pub fn scan_numbers(value: &str) -> Vec<f64> {
    let characters: Vec<char> = value.chars().collect();
    let mut numbers = Vec::new();
    let mut index = 0;
    while index < characters.len() {
        let start = index;
        let mut token = String::new();
        let character = characters[index];
        if is_minus(character) {
            token.push('-');
            index += 1;
        }
        if index >= characters.len() || !characters[index].is_ascii_digit() {
            index = start + 1;
            continue;
        }
        while index < characters.len() && characters[index].is_ascii_digit() {
            token.push(characters[index]);
            index += 1;
        }
        loop {
            let mut next = index;
            while next < characters.len() && is_space(characters[next]) {
                next += 1;
            }
            if next == index || next + 3 > characters.len() {
                break;
            }
            if (next..next + 3).all(|position| characters[position].is_ascii_digit())
                && (next + 3 == characters.len()
                    || !characters[next + 3].is_ascii_digit())
            {
                token.push(' ');
                for position in next..next + 3 {
                    token.push(characters[position]);
                }
                index = next + 3;
                continue;
            }
            break;
        }
        if index < characters.len()
            && (characters[index] == ',' || characters[index] == '.')
            && index + 1 < characters.len()
            && characters[index + 1].is_ascii_digit()
        {
            token.push('.');
            index += 1;
            while index < characters.len() && characters[index].is_ascii_digit() {
                token.push(characters[index]);
                index += 1;
            }
        }
        let cleaned = token.replace(' ', "");
        if let Ok(number) = cleaned.parse::<f64>() {
            numbers.push(number);
        }
        if index == start {
            index += 1;
        }
    }
    numbers
}

/// Zone classification copied from `tns_core::classify_zone`.
///
/// ODN is checked first, then night, then day; anything unknown is ODN.
/// Latin `t`/`c` are folded to Cyrillic `т`/`с` like the legacy code.
pub fn classify_zone(zone: &str) -> Zone {
    let normalized = zone
        .to_lowercase()
        .replace('\u{00a0}', " ")
        .replace('t', "т")
        .replace('c', "с");
    if normalized.is_empty() {
        return Zone::Odn;
    }
    if [
        "одн",
        "общедомовые",
        "место общего пользования",
        "без дифференциации",
    ]
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Zone {
    Day,
    Night,
    Odn,
}

impl Zone {
    pub fn as_str(&self) -> &'static str {
        match self {
            Zone::Day => "day",
            Zone::Night => "night",
            Zone::Odn => "odn",
        }
    }
}

pub fn preview_bucket(zone: &str) -> &'static str {
    match classify_zone(zone) {
        Zone::Day => "day",
        Zone::Night => "night",
        Zone::Odn => "odn",
    }
}

/// Sub-abonent marker is the Latin letter `C` in the sub-type cell.
pub fn is_sub(sub_type: &str) -> bool {
    sub_type.trim().to_uppercase() == "C"
}

/// A non-sub meter with no billed volume is a reserve meter.
pub fn is_reserve(sub: bool, billed: Option<f64>) -> bool {
    !sub && billed.unwrap_or(0.0) == 0.0
}

const MONTHS: [(&str, u32); 12] = [
    ("январь", 1),
    ("февраль", 2),
    ("март", 3),
    ("апрель", 4),
    ("май", 5),
    ("июнь", 6),
    ("июль", 7),
    ("август", 8),
    ("сентябрь", 9),
    ("октябрь", 10),
    ("ноябрь", 11),
    ("декабрь", 12),
];

/// Extract `Октябрь 2026` -> (`2026-10`, `Октябрь 2026`).
pub fn parse_month(label: &str) -> Option<(String, String)> {
    let normalized = normalize_text(label);
    let words: Vec<&str> = normalized.split(' ').collect();
    for pair in words.windows(2) {
        let lower = pair[0].to_lowercase();
        let Some(month) = MONTHS
            .iter()
            .find(|(name, _)| *name == lower)
            .map(|(_, number)| *number)
        else {
            continue;
        };
        if pair[1].len() != 4 || !pair[1].chars().all(|character| character.is_ascii_digit())
        {
            continue;
        }
        let mut characters = pair[0].chars();
        let month_label = match characters.next() {
            Some(first) => format!(
                "{}{} {}",
                first.to_uppercase(),
                characters.as_str(),
                pair[1]
            ),
            None => continue,
        };
        return Some((format!("{}-{month:02}", pair[1]), month_label));
    }
    None
}

/// Parse `стр. 2 из 82` (or `стр 2 из 82`) into `(2, 82)`.
pub fn parse_footer(text: &str) -> Option<(u32, u32)> {
    let normalized = normalize_text(text);
    let start = normalized
        .find("стр.")
        .or_else(|| normalized.find("стр "))?;
    let rest = &normalized[start..];
    let mut words = rest.split(' ');
    let label = words.next()?;
    if !label.starts_with("стр") {
        return None;
    }
    let mut numbers = words.filter_map(|word| {
        let digits: String = word
            .chars()
            .filter(|character| character.is_ascii_digit())
            .collect();
        digits.parse::<u32>().ok()
    });
    Some((numbers.next()?, numbers.next()?))
}

fn is_space(character: char) -> bool {
    character.is_whitespace() || character == '\u{00a0}'
}

fn is_minus(character: char) -> bool {
    matches!(
        character,
        '\u{2212}'
            | '-'
            | '\u{2010}'
            | '\u{2011}'
            | '\u{2012}'
            | '\u{2013}'
            | '\u{2014}'
            | '\u{2015}'
            | '\u{FE63}'
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalises_nbsp_and_line_breaks() {
        assert_eq!(normalize_text("  Итого:\r\n\u{00a0}1  032\t745,77 "), "Итого: 1 032 745,77");
        assert_eq!(normalize_text(""), "");
    }

    #[test]
    fn strips_all_whitespace() {
        assert_eq!(strip_whitespace("0078 800450\u{00a0}00064"), "007880045000064");
    }

    #[test]
    fn parses_cell_numbers() {
        assert_eq!(parse_number("1 234,56"), Some(1234.56));
        assert_eq!(parse_number("1\u{00a0}234,56"), Some(1234.56));
        assert_eq!(parse_number("\u{2212}12,5"), Some(-12.5));
        assert_eq!(parse_number("–12,5"), Some(-12.5));
        assert_eq!(parse_number("—12,5"), Some(-12.5));
        assert_eq!(parse_number("-"), None);
        assert_eq!(parse_number(".."), None);
        assert_eq!(parse_number(""), None);
        assert_eq!(parse_number("21170"), Some(21170.0));
    }

    #[test]
    fn scans_separate_total_numbers() {
        assert_eq!(
            scan_numbers("Итого: 736 051,312 4 309 766,80"),
            vec![736051.312, 4309766.8]
        );
    }

    #[test]
    fn scans_glued_total_numbers() {
        assert_eq!(
            scan_numbers("223 073,372 1 159 713,33"),
            vec![223073.372, 1159713.33]
        );
        assert_eq!(
            scan_numbers("Итого: 1 032 745,77 5 419 801,94"),
            vec![1032745.77, 5419801.94]
        );
    }

    #[test]
    fn scans_negative_numbers() {
        assert_eq!(scan_numbers("-2 311,996"), vec![-2311.996]);
    }

    #[test]
    fn classifies_zones_like_core() {
        assert_eq!(classify_zone("День"), Zone::Day);
        assert_eq!(classify_zone("Т1"), Zone::Day);
        assert_eq!(classify_zone("Пик"), Zone::Day);
        assert_eq!(classify_zone("Ночь"), Zone::Night);
        assert_eq!(classify_zone("Т2"), Zone::Night);
        assert_eq!(classify_zone("t2"), Zone::Night);
        assert_eq!(classify_zone("ОДН"), Zone::Odn);
        assert_eq!(classify_zone(""), Zone::Odn);
        assert_eq!(classify_zone("Одноставочный"), Zone::Odn);
        assert_eq!(classify_zone("Общедомовые нужды"), Zone::Odn);
    }

    #[test]
    fn detects_sub_rows_and_reserve_meters() {
        assert!(is_sub(" C "));
        assert!(!is_sub(""));
        assert!(!is_sub("С")); // Cyrillic С is not the Latin marker
        assert!(is_reserve(false, Some(0.0)));
        assert!(is_reserve(false, None));
        assert!(!is_reserve(false, Some(1.0)));
        assert!(!is_reserve(true, Some(0.0)));
    }

    #[test]
    fn parses_month_label() {
        assert_eq!(
            parse_month("Октябрь 2026"),
            Some(("2026-10".to_string(), "Октябрь 2026".to_string()))
        );
        assert_eq!(
            parse_month("октябрь 2026 г."),
            Some(("2026-10".to_string(), "Октябрь 2026".to_string()))
        );
        assert_eq!(parse_month("нет даты"), None);
    }

    #[test]
    fn parses_footer_sequence() {
        assert_eq!(parse_footer("... стр. 2 из 82"), Some((2, 82)));
        assert_eq!(parse_footer("стр 81 из 82"), Some((81, 82)));
        assert_eq!(parse_footer("нет футера"), None);
    }
}
