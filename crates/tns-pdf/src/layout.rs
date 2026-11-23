//! Vector-grid geometry: table rules, column boundaries, row bands.

use crate::pdfium::{PathObject, Segment, TextPage, VisibleChar};
use std::collections::BTreeMap;

pub const COLUMNS: usize = 27;
pub const VERTICAL_TOLERANCE: f64 = 1.0;
pub const HORIZONTAL_TOLERANCE: f64 = 1.0;

#[derive(Debug, Clone)]
pub struct NumberRow {
    pub centers: Vec<f64>,
    pub bottom: f64,
    pub top: f64,
}

#[derive(Debug, Clone)]
pub struct PageGeometry {
    pub width: f64,
    pub height: f64,
    /// Column boundaries, 28 values for a valid table page.
    pub x_boundaries: Vec<f64>,
    /// Full-width horizontal rules, top-down (descending page-space y).
    pub horizontal_lines: Vec<f64>,
    /// True when 28 vertical clusters were derived from vector rules.
    pub exact_verticals: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct Band {
    pub top: f64,
    pub bottom: f64,
}

impl Band {
    pub fn height(&self) -> f64 {
        self.top - self.bottom
    }
}

#[derive(Debug, Clone)]
pub struct Grid {
    pub x_boundaries: Vec<f64>,
    pub header_bottom: f64,
    pub bands: Vec<Band>,
}

/// Derive full-width horizontal rules and vertical column boundaries.
pub fn page_geometry(paths: &[PathObject], width: f64, height: f64) -> PageGeometry {
    let mut verticals = Vec::new();
    let mut horizontals = Vec::new();
    for path in paths {
        let mut previous: Option<Segment> = None;
        for segment in &path.segments {
            if let Some(previous) = previous {
                if segment.is_lineto() {
                    let dx = (segment.x - previous.x).abs() as f64;
                    let dy = (segment.y - previous.y).abs() as f64;
                    if dy <= 0.5 && dx > 0.9 * width {
                        horizontals.push((previous.y as f64 + segment.y as f64) / 2.0);
                    }
                    if dx <= 0.5 && dy > 20.0 {
                        verticals.push((previous.x as f64 + segment.x as f64) / 2.0);
                    }
                }
            }
            previous = Some(*segment);
        }
    }
    let horizontal_lines = cluster_desc(&horizontals, HORIZONTAL_TOLERANCE);
    let vertical = cluster_asc(&verticals, VERTICAL_TOLERANCE);
    PageGeometry {
        width,
        height,
        exact_verticals: vertical.len() == COLUMNS + 1,
        x_boundaries: vertical,
        horizontal_lines,
    }
}

/// Cluster sorted-or-not values with a tolerance, returning ascending centers.
pub fn cluster_asc(values: &[f64], tolerance: f64) -> Vec<f64> {
    let mut sorted: Vec<f64> = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mut clusters: Vec<Vec<f64>> = Vec::new();
    for value in sorted {
        match clusters.last_mut() {
            Some(cluster) if value - *cluster.last().expect("non-empty cluster") <= tolerance => {
                cluster.push(value);
            }
            _ => clusters.push(vec![value]),
        }
    }
    clusters
        .into_iter()
        .map(|cluster| cluster.iter().sum::<f64>() / cluster.len() as f64)
        .collect()
}

/// Cluster values with a tolerance, returning descending centers.
pub fn cluster_desc(values: &[f64], tolerance: f64) -> Vec<f64> {
    let mut clusters = cluster_asc(values, tolerance);
    clusters.reverse();
    clusters
}

/// Fallback column boundaries: midpoints between the 1..27 header numbers,
/// extended by 20 pt on both sides.
pub fn fallback_boundaries(centers: &[f64]) -> Vec<f64> {
    if centers.len() != COLUMNS {
        return Vec::new();
    }
    let mut boundaries = Vec::with_capacity(COLUMNS + 1);
    boundaries.push(centers[0] - 20.0);
    for pair in centers.windows(2) {
        boundaries.push((pair[0] + pair[1]) / 2.0);
    }
    boundaries.push(centers[COLUMNS - 1] + 20.0);
    boundaries
}

/// First full-width rule below the column-number row.
pub fn header_bottom(lines_desc: &[f64], number_row: Option<&NumberRow>) -> Option<f64> {
    match number_row {
        Some(number_row) => lines_desc
            .iter()
            .copied()
            .find(|y| *y < number_row.bottom + 1.0),
        // Header repeat: title/header top, number-row top, number-row bottom.
        None => lines_desc.get(2).copied(),
    }
}

/// Data bands between consecutive full-width rules below the header.
pub fn data_bands(lines_desc: &[f64], header_bottom: f64) -> Vec<Band> {
    let below: Vec<f64> = lines_desc
        .iter()
        .copied()
        .filter(|y| *y < header_bottom)
        .collect();
    let mut bands = Vec::new();
    if let Some(first) = below.first() {
        bands.push(Band {
            top: header_bottom,
            bottom: *first,
        });
    }
    for pair in below.windows(2) {
        bands.push(Band {
            top: pair[0],
            bottom: pair[1],
        });
    }
    bands
        .into_iter()
        .filter(|band| band.height() > 2.0)
        .collect()
}

/// Locate the header row of column numbers 1..27.
///
/// Characters are grouped by vertical centre, tokenised by small x gaps, and
/// the topmost candidate with all values 1..27 in ascending x order wins.
pub fn number_row(text: &TextPage<'_>) -> Option<NumberRow> {
    #[derive(Clone, Copy)]
    struct Glyph {
        left: f64,
        right: f64,
        bottom: f64,
        top: f64,
        value: u32,
    }

    let count = text.count_chars();
    let mut glyphs = Vec::new();
    for index in 0..count {
        let value = text.unicode(index);
        if !(value >= '0' as u32 && value <= '9' as u32) {
            continue;
        }
        if let Some((left, right, bottom, top)) = text.char_box(index) {
            glyphs.push(Glyph {
                left,
                right,
                bottom,
                top,
                value: value - '0' as u32,
            });
        }
    }
    glyphs.sort_by(|a, b| {
        let ay = (a.bottom + a.top) / 2.0;
        let by = (b.bottom + b.top) / 2.0;
        ay.partial_cmp(&by).unwrap_or(std::cmp::Ordering::Equal)
    });

    let mut rows: Vec<(f64, f64, Vec<Glyph>)> = Vec::new();
    for glyph in glyphs {
        let center = (glyph.bottom + glyph.top) / 2.0;
        match rows.last_mut() {
            Some((center_y, _, row)) if (center - *center_y).abs() <= 1.5 => {
                *center_y = (*center_y + center) / 2.0;
                row.push(glyph);
            }
            _ => rows.push((center, center, vec![glyph])),
        }
    }

    let mut candidates = Vec::new();
    for (_, _, mut row) in rows {
        row.sort_by(|a, b| a.left.partial_cmp(&b.left).unwrap_or(std::cmp::Ordering::Equal));
        let mut tokens: Vec<(f64, u32, f64, f64)> = Vec::new();
        let mut index = 0;
        while index < row.len() {
            let start = index;
            let mut value = row[index].value;
            let mut right = row[index].right;
            while index + 1 < row.len() && row[index + 1].left - right <= 2.0 {
                index += 1;
                value = value.saturating_mul(10).saturating_add(row[index].value);
                right = row[index].right;
            }
            tokens.push((
                (row[start].left + right) / 2.0,
                value,
                row[start].bottom,
                row[start].top,
            ));
            index += 1;
        }
        if tokens.len() != COLUMNS {
            continue;
        }
        let mut by_value: BTreeMap<u32, f64> = BTreeMap::new();
        for (x, value, _, _) in &tokens {
            by_value.entry(*value).or_insert(*x);
        }
        if by_value.len() != COLUMNS
            || !(1..=COLUMNS as u32).all(|value| by_value.contains_key(&value))
        {
            continue;
        }
        let centers: Vec<f64> = (1..=COLUMNS as u32)
            .map(|value| *by_value.get(&value).expect("checked above"))
            .collect();
        if centers.windows(2).all(|pair| pair[0] < pair[1]) {
            candidates.push(NumberRow {
                centers,
                bottom: tokens.iter().map(|token| token.2).fold(f64::MAX, f64::min),
                top: tokens.iter().map(|token| token.3).fold(f64::MIN, f64::max),
            });
        }
    }
    candidates.into_iter().max_by(|a, b| {
        a.bottom
            .partial_cmp(&b.bottom)
            .unwrap_or(std::cmp::Ordering::Equal)
    })
}

/// Plain page text in PDFium character order, decoded with surrogate pairs.
pub fn page_text(text: &TextPage<'_>) -> String {    let count = text.count_chars();
    let mut output = String::with_capacity(count);
    let mut index = 0;
    while index < count {
        let value = text.unicode(index);
        if (0xD800..=0xDBFF).contains(&value) && index + 1 < count {
            let low = text.unicode(index + 1);
            if (0xDC00..=0xDFFF).contains(&low) {
                let code = 0x10000 + ((value - 0xD800) << 10) + (low - 0xDC00);
                output.push(char::from_u32(code).unwrap_or('\u{FFFD}'));
                index += 2;
                continue;
            }
        }
        output.push(char::from_u32(value).unwrap_or('\u{FFFD}'));
        index += 1;
    }
    output
}

/// Text of visible characters whose centre falls inside the rectangle.
///
/// Whitespace characters only need to be inside the vertical band; this keeps
/// line breaks between words of the same multi-line cell.
pub fn text_in_rect(
    characters: &[VisibleChar],
    left: f64,
    top: f64,
    right: f64,
    bottom: f64,
) -> String {
    let mut output = String::new();
    for character in characters {
        let center_x = (character.left + character.right) / 2.0;
        let center_y = (character.bottom + character.top) / 2.0;
        if center_y < bottom || center_y > top {
            continue;
        }
        if character.character.is_whitespace() {
            output.push(' ');
        } else if center_x >= left && center_x <= right {
            output.push(character.character);
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clusters_vertical_rules_with_tolerance() {
        let values = [28.0, 28.4, 28.9, 67.0, 67.6, 145.0];
        assert_eq!(cluster_asc(&values, 1.0), vec![28.433333333333334, 67.3, 145.0]);
    }

    #[test]
    fn clusters_horizontal_rules_top_down() {
        let values = [467.62, 477.01, 477.4, 517.63];
        assert_eq!(cluster_desc(&values, 1.0), vec![517.63, 477.205, 467.62]);
    }

    #[test]
    fn builds_last_page_bands_with_five_rules() {
        let lines = [560.89, 523.92, 517.63, 477.01, 467.62];
        let hb = header_bottom(&lines, None).expect("header");
        assert_eq!(hb, 517.63);
        let bands = data_bands(&lines, hb);
        assert_eq!(bands.len(), 2);
        assert_eq!(bands[0].top, 517.63);
        assert_eq!(bands[0].bottom, 477.01);
        assert_eq!(bands[1].bottom, 467.62);
    }

    #[test]
    fn fallback_boundaries_extend_number_centers() {
        let centers: Vec<f64> = (0..27).map(|i| 30.0 + i as f64 * 10.0).collect();
        let boundaries = fallback_boundaries(&centers);
        assert_eq!(boundaries.len(), 28);
        assert_eq!(boundaries[0], 10.0);
        assert_eq!(boundaries[1], 35.0);
        assert_eq!(boundaries[27], 290.0 + 20.0);
    }

    #[test]
    #[ignore]
    fn probe_real_fixture_geometry() {
        let path = std::env::var("TNS_PDF_FIXTURE").expect("TNS_PDF_FIXTURE");
        let document = crate::pdfium::Document::open(std::path::Path::new(&path))
            .expect("open fixture");
        for index in [0usize, 1, 81] {
            let page = document.page(index).expect("page");
            let text = page.text_page().expect("text page");
            let numbers = number_row(&text);
            let geometry =
                page_geometry(&page.paths(), page.width(), page.height());
            let grid = numbers.as_ref().and_then(|numbers| {
                header_bottom(&geometry.horizontal_lines, Some(numbers))
            });
            let bands = grid.map(|header| {
                data_bands(&geometry.horizontal_lines, header).len()
            });
            println!(
                "page {}: x={} lines={} numbers={:?} header={:?} bands={:?} text={}",
                index + 1,
                geometry.x_boundaries.len(),
                geometry.horizontal_lines.len(),
                numbers.as_ref().map(|n| n.centers.len()),
                grid,
                bands,
                page_text(&text).chars().count(),
            );
        }
    }
}
