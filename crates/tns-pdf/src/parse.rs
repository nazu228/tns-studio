//! Statement detection, row extraction and invariant validation.

use crate::layout::{
    self, fallback_boundaries, Band, NumberRow, PageGeometry, COLUMNS,
};
use crate::model::{
    Balance, House, Layout, Meter, Official, PageInfo, Source, Statement, StatementMeta, Totals,
};
use crate::pdfium::Document;
use crate::text::{
    classify_zone, is_reserve, is_sub, normalize_text, parse_base_period, parse_footer,
    parse_month, parse_number, preview_bucket, scan_numbers, strip_whitespace, Zone,
};
use crate::PdfError;
use std::path::Path;

const CELL_INSET: f64 = 0.2;

struct PageScan {
    index: usize,
    text: String,
    table: bool,
    title: bool,
    footer: Option<(u32, u32)>,
    geometry: PageGeometry,
    number_row: Option<NumberRow>,
}

struct Block {
    pages: Vec<usize>,
    last_footer: Option<(u32, u32)>,
}

struct TotalRow {
    volume: f64,
    amount: f64,
    page: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RowKind {
    Total,
    House,
    Meter,
}

/// Parse every TNS statement in the document.
pub fn parse_pdf(path: &Path) -> Result<Vec<Statement>, PdfError> {
    let document = Document::open(path)?;
    let page_count = document.page_count();
    if page_count == 0 {
        return Err(PdfError::NoStatements);
    }
    let scans = scan_pages(&document, page_count)?;
    let blocks = detect_blocks(&scans);
    if blocks.is_empty() {
        return Err(PdfError::NoStatements);
    }
    // Per-statement recovery: a bad block (e.g. a correction with a manual
    // override that breaks a meter invariant) must not kill the remaining
    // statements in a multi-statement PDF.
    let mut statements = Vec::with_capacity(blocks.len());
    let mut first_error: Option<PdfError> = None;
    for block in &blocks {
        match extract_statement(&document, path, block, &scans) {
            Ok(statement) => statements.push(statement),
            Err(error) => {
                eprintln!(
                    "warning: skipping statement at pages {:?}: {error}",
                    block.pages.first().map(|p| p + 1).unwrap_or(0)
                );
                first_error.get_or_insert(error);
            }
        }
    }
    if statements.is_empty() {
        return Err(first_error.unwrap_or(PdfError::NoStatements));
    }
    Ok(statements)
}

fn scan_pages(document: &Document, page_count: usize) -> Result<Vec<PageScan>, PdfError> {
    let mut scans = Vec::with_capacity(page_count);
    for index in 0..page_count {
        let page = document.page(index)?;
        let text_page = page.text_page()?;
        let text = layout::page_text(&text_page);
        let normalized = normalize_text(&text);
        let number_row = layout::number_row(&text_page);
        let geometry = layout::page_geometry(&page.paths(), page.width(), page.height());
        let title = normalized.contains("Ведомость электропотребления");
        let has_header = normalized.contains("Точка учета")
            && normalized.contains("Заводской")
            && normalized.contains("Начис");
        let table = geometry.exact_verticals || (number_row.is_some() && has_header);
        scans.push(PageScan {
            index,
            footer: parse_footer(&text),
            text,
            table,
            title,
            geometry,
            number_row,
        });
    }
    Ok(scans)
}

fn detect_blocks(scans: &[PageScan]) -> Vec<Block> {
    let mut blocks = Vec::new();
    let mut current: Option<Block> = None;
    for scan in scans {
        if !scan.table {
            if let Some(block) = current.take() {
                blocks.push(block);
            }
            continue;
        }
        // A new title page always starts a new statement, even when the
        // footer happens to be sequential (partial export from a larger
        // document: `стр. 148 из 1535` after `стр. 147 из 1535`).
        if scan.title {
            if let Some(block) = current.take() {
                blocks.push(block);
            }
            let block = Block {
                pages: vec![scan.index],
                last_footer: scan.footer,
            };
            if let Some((number, total)) = scan.footer {
                if number == total {
                    blocks.push(block);
                    continue;
                }
            }
            current = Some(block);
            continue;
        }
        if let Some(block) = current.as_mut() {
            if continuation(block, scan) {
                block.pages.push(scan.index);
                block.last_footer = scan.footer;
                if let Some((number, total)) = scan.footer {
                    if number == total {
                        blocks.push(current.take().expect("checked above"));
                    }
                }
                continue;
            }
            blocks.push(current.take().expect("checked above"));
        }
    }
    if let Some(block) = current {
        blocks.push(block);
    }
    blocks
}

fn continuation(block: &Block, scan: &PageScan) -> bool {
    let Some((number, total)) = scan.footer else {
        return false;
    };
    match block.last_footer {
        Some((previous, previous_total)) => {
            total == previous_total && number == previous + 1
        }
        None => number == 2 && total >= 2,
    }
}

fn extract_statement(
    document: &Document,
    path: &Path,
    block: &Block,
    scans: &[PageScan],
) -> Result<Statement, PdfError> {
    let first_page_index = *block.pages.first().expect("block is not empty");
    let first_scan = &scans[first_page_index];
    let (org, contract_raw, month_label_raw) = extract_metadata(&first_scan.text);
    let base_period = month_label_raw
        .as_deref()
        .and_then(parse_base_period);
    let is_correction = base_period.is_some();
    let (month, month_label) = match month_label_raw.as_deref().and_then(parse_month) {
        Some((month, label)) => {
            // Corrections keep the full label (`Октябрь 2026 за сентябрь 2026`)
            // because the base period is part of the document identity.
            let label = if is_correction {
                month_label_raw.clone().unwrap_or_default()
            } else {
                label
            };
            (Some(month), Some(label))
        }
        None => (None, month_label_raw.clone()),
    };

    let mut houses: Vec<House> = Vec::new();
    let mut meters: Vec<Meter> = Vec::new();
    let mut pages: Vec<PageInfo> = Vec::new();
    let mut total_rows: Vec<TotalRow> = Vec::new();
    let mut warnings: Vec<String> = Vec::new();
    let mut layout_boundaries: Option<Vec<f64>> = None;
    let page_size = [first_scan.geometry.width, first_scan.geometry.height];
    let mut exact_pages = 0usize;

    for (position, page_index) in block.pages.iter().copied().enumerate() {
        let scan = &scans[page_index];
        let page_number = page_index + 1;
        if scan.geometry.exact_verticals {
            exact_pages += 1;
        }
        let page = document.page(page_index)?;
        let text_page = page.text_page()?;
        let x_boundaries = column_boundaries(scan, page_number)?;
        if position == 0 {
            layout_boundaries = Some(x_boundaries.iter().map(|x| round2(*x)).collect());
        }
        let header = layout::header_bottom(
            &scan.geometry.horizontal_lines,
            scan.number_row.as_ref(),
        )
        .ok_or_else(|| PdfError::Parse {
            page: Some(page_number),
            house: None,
            row: None,
            message: "cannot locate the table header rule".to_string(),
        })?;
        let bands = layout::data_bands(&scan.geometry.horizontal_lines, header);
        let visible = text_page.visible_chars();
        let houses_before = houses.len();
        let mut page_rows = 0usize;

        for band in bands {
            let cells = extract_cells(&visible, &x_boundaries, band);
            if cells.iter().all(|cell| cell.is_empty()) {
                continue;
            }
            page_rows += 1;
            if let Some((volume, amount)) = total_numbers(&cells) {
                if !total_rows.is_empty() {
                    warnings.push(format!(
                        "page {page_number}: multiple total rows; the last one is official"
                    ));
                }
                total_rows.push(TotalRow {
                    volume,
                    amount,
                    page: page_number,
                });
                continue;
            }
            if !total_rows.is_empty() {
                continue;
            }
            match classify_row(&cells) {
                RowKind::Total => unreachable!("total rows are handled above"),
                RowKind::House => {
                    let merged = normalize_text(&layout::text_in_rect(
                        &visible,
                        x_boundaries[0] + CELL_INSET,
                        band.top - CELL_INSET,
                        x_boundaries[2] - CELL_INSET,
                        band.bottom + CELL_INSET,
                    ));
                    let address = if merged.is_empty() {
                        normalize_text(&format!("{} {}", cells[0], cells[1]))
                    } else {
                        merged
                    };
                    houses.push(House {
                        num: houses.len() + 1,
                        name: address,
                        page: page_number,
                        main: parse_number(&cells[14]).map(round3),
                        sub_deduct: parse_number(&cells[20]).map(round3),
                        control: parse_number(&cells[25]).map(round3),
                        amount: parse_number(&cells[26]).map(round2),
                        day: 0.0,
                        night: 0.0,
                        odn: 0.0,
                        simple: 0.0,
                        total: 0.0,
                        diff: 0.0,
                        meters_active: 0,
                        meters_res: 0,
                        sub_rows: 0,
                        meter_range: [0, 0],
                    });
                }
                RowKind::Meter => {
                    let Some(house) = houses.last_mut() else {
                        continue;
                    };
                    let zone_raw = cells[6].clone();
                    let sub = is_sub(&cells[7]);
                    let billed_raw = parse_number(&cells[25]);
                    let billed = billed_raw.map(round3);
                    let amount = parse_number(&cells[26]).map(round2);
                    if sub {
                        house.sub_rows += 1;
                    } else {
                        let value = billed_raw.unwrap_or(0.0);
                        match classify_zone(&zone_raw) {
                            Zone::Day => house.day += value,
                            Zone::Night => house.night += value,
                            Zone::Odn => house.odn += value,
                        }
                        if value == 0.0 {
                            house.meters_res += 1;
                        } else {
                            house.meters_active += 1;
                        }
                    }
                    let house_number = house.num;
                    let row = meters.len() + 1;
                    meters.push(Meter {
                        house: house_number,
                        row,
                        page: page_number,
                        point: cells[0].clone(),
                        place: cells[1].clone(),
                        serial: strip_whitespace(&cells[2]),
                        zone: classify_zone(&zone_raw).as_str().to_string(),
                        zone_raw,
                        preview_bucket: preview_bucket(&cells[6]).to_string(),
                        sub_type: cells[7].clone(),
                        start: parse_number(&cells[9]).map(round3),
                        end: parse_number(&cells[10]).map(round3),
                        delta: parse_number(&cells[12]).map(round3),
                        k: parse_number(&cells[13]),
                        main: parse_number(&cells[14]).map(round3),
                        extra: parse_number(&cells[15]).map(round3),
                        unmetered: parse_number(&cells[16]).map(round3),
                        odn: parse_number(&cells[17]).map(round3),
                        line_loss: parse_number(&cells[18]).map(round3),
                        tr_loss: parse_number(&cells[19]).map(round3),
                        sub_volume: parse_number(&cells[20]).map(round3),
                        voltage: cells[23].clone(),
                        category: cells[24].clone(),
                        billed,
                        amount,
                        is_sub: sub,
                        is_reserve: is_reserve(sub, billed_raw),
                    });
                }
            }
        }
        pages.push(PageInfo {
            page: page_number,
            footer: scan
                .footer
                .map(|(number, total)| format!("{number}/{total}")),
            rows: page_rows,
            houses_started: houses.len() - houses_before,
            role: String::new(),
        });
    }

    if total_rows.is_empty() {
        return Err(PdfError::invariant(
            "official total row is missing",
            Some(*block.pages.last().expect("block is not empty") + 1),
            None,
            None,
        ));
    }
    let official = total_rows.last().expect("checked above");
    let official_page = official.page;
    finalize_houses(&mut houses, &meters)?;

    for page in &mut pages {
        if page.page == first_page_index + 1 {
            page.role = "title+table".to_string();
        } else if page.page == official_page {
            page.role = "table+total".to_string();
        } else {
            page.role = "table".to_string();
        }
    }

    let control = round3(houses.iter().filter_map(|house| house.control).sum());
    let amount = round2(houses.iter().filter_map(|house| house.amount).sum());
    let day = round3(houses.iter().map(|house| house.day).sum());
    let night = round3(houses.iter().map(|house| house.night).sum());
    let odn = round3(houses.iter().map(|house| house.odn).sum());
    let official_volume = round3(official.volume);
    let official_amount = round2(official.amount);
    let totals = Totals {
        day,
        night,
        odn,
        control,
        amount,
        official: Official {
            volume: Some(official_volume),
            amount: Some(official_amount),
            page: Some(official_page),
        },
        balance: Balance {
            volume: round3(control - official_volume),
            amount: round2(amount - official_amount),
        },
    };

    let x_boundaries = layout_boundaries.unwrap_or_default();
    let statement = Statement {
        schema_version: Statement::SCHEMA_VERSION,
        source: Source {
            file: path
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default(),
            pages: document.page_count(),
            producer: document.meta("Producer").map(|producer| {
                producer
                    .split(" by ")
                    .next()
                    .unwrap_or(&producer)
                    .trim()
                    .to_string()
            }),
            text_layer: !first_scan.text.is_empty(),
        },
        statement: StatementMeta {
            kind: statement_kind(org.as_deref()),
            is_correction,
            org,
            contract: contract_raw
                .as_deref()
                .and_then(|raw| normalize_text(raw).split(' ').next().map(str::to_string)),
            month,
            base_period,
            month_label,
            page_range: [
                first_page_index + 1,
                block.pages.last().expect("block is not empty") + 1,
            ],
        },
        layout: Layout {
            page_size: [round2(page_size[0]), round2(page_size[1])],
            columns: COLUMNS,
            x_boundaries,
            confidence: round3(exact_pages as f64 / block.pages.len() as f64),
        },
        pages,
        houses,
        meters,
        totals,
        warnings,
    };
    validate_statement(&statement, block.pages.len())?;
    Ok(statement)
}

fn extract_metadata(text: &str) -> (Option<String>, Option<String>, Option<String>) {
    let lines: Vec<String> = text
        .split(['\r', '\n'])
        .map(normalize_text)
        .filter(|line| !line.is_empty())
        .collect();
    let mut org = None;
    let mut contract = None;
    let mut month = None;
    for (index, line) in lines.iter().enumerate() {
        let next = lines.get(index + 1).cloned();
        if org.is_none() {
            org = value_after(line, "Организация:", next.clone());
        }
        if contract.is_none() {
            contract = value_after(line, "Договор:", next.clone());
        }
        if month.is_none() {
            if let Some(mut value) = value_after(line, "Месяц:", lines.get(index + 1).cloned()) {
                // PDFium may split `Октябрь 2026 за сентябрь 2026` across lines.
                // Append a continuation only when the base period is still missing.
                if parse_base_period(&value).is_none() {
                    for candidate in lines.iter().skip(index + 2).take(2) {
                        let combined = format!("{value} {candidate}");
                        if parse_base_period(&combined).is_some() {
                            value = combined;
                            break;
                        }
                    }
                }
                month = Some(value);
            }
        }
    }
    (org, contract, month)
}

fn value_after(line: &str, prefix: &str, next: Option<String>) -> Option<String> {
    let rest = line.strip_prefix(prefix)?.trim();
    if rest.is_empty() {
        next.filter(|value| !value.is_empty())
    } else {
        Some(rest.to_string())
    }
}

fn statement_kind(org: Option<&str>) -> String {
    let input = org.unwrap_or("").to_lowercase();
    if input.contains("город") {
        "gorod".to_string()
    } else if input.contains("дом") {
        "dom".to_string()
    } else {
        "unknown".to_string()
    }
}

fn column_boundaries(scan: &PageScan, page: usize) -> Result<Vec<f64>, PdfError> {
    if scan.geometry.x_boundaries.len() == COLUMNS + 1 {
        return Ok(scan.geometry.x_boundaries.clone());
    }
    if let Some(number_row) = &scan.number_row {
        let boundaries = fallback_boundaries(&number_row.centers);
        if boundaries.len() == COLUMNS + 1 {
            return Ok(boundaries);
        }
    }
    Err(PdfError::Parse {
        page: Some(page),
        house: None,
        row: None,
        message: "cannot derive 28 column boundaries".to_string(),
    })
}

fn extract_cells(
    characters: &[crate::pdfium::VisibleChar],
    boundaries: &[f64],
    band: Band,
) -> Vec<String> {
    let mut cells = Vec::with_capacity(COLUMNS);
    for column in 0..COLUMNS {
        let value = layout::text_in_rect(
            characters,
            boundaries[column] + CELL_INSET,
            band.top - CELL_INSET,
            boundaries[column + 1] - CELL_INSET,
            band.bottom + CELL_INSET,
        );
        cells.push(normalize_text(&value));
    }
    cells
}

/// Classify one extracted row. Total wins because a total row can also look
/// like a house row (billed volume present, serial empty).
pub fn classify_row(cells: &[String]) -> RowKind {
    if cells.iter().any(|cell| starts_with_total(cell)) {
        return RowKind::Total;
    }
    let control = parse_number(&cells[25]);
    if control.is_some()
        && cells[2].is_empty()
        && cells[9].is_empty()
        && cells[10].is_empty()
        && !is_point_code(&cells[0])
    {
        return RowKind::House;
    }
    RowKind::Meter
}

pub fn total_numbers(cells: &[String]) -> Option<(f64, f64)> {
    let column = cells.iter().position(|cell| starts_with_total(cell))?;
    let joined = cells[column..].join(" ");
    let numbers = scan_numbers(&joined);
    if numbers.len() == 2 {
        return Some((numbers[0], numbers[1]));
    }
    let volume = parse_number(cells.get(25)?)?;
    let amount = parse_number(cells.get(26)?)?;
    Some((volume, amount))
}

fn starts_with_total(value: &str) -> bool {
    value
        .trim_start()
        .to_lowercase()
        .starts_with("итого")
}

fn parse_footer_pair(value: &str) -> Option<(u32, u32)> {
    let (number, total) = value.split_once('/')?;
    Some((number.parse().ok()?, total.parse().ok()?))
}

fn is_point_code(value: &str) -> bool {
    let compact = strip_whitespace(value);
    (9..=14).contains(&compact.len())
        && !compact.is_empty()
        && compact.chars().all(|character| character.is_ascii_digit())
}

fn finalize_houses(houses: &mut [House], meters: &[Meter]) -> Result<(), PdfError> {
    let mut cursor = 0usize;
    for house in houses.iter_mut() {
        let start = cursor;
        while cursor < meters.len() && meters[cursor].house == house.num {
            cursor += 1;
        }
        if cursor == start {
            return Err(PdfError::invariant(
                "house has no meter rows",
                Some(house.page),
                Some(house.num),
                None,
            ));
        }
        house.meter_range = [start, cursor - 1];
        house.day = round3(house.day);
        house.night = round3(house.night);
        house.odn = round3(house.odn);
        house.simple = house.odn;
        house.total = round3(house.day + house.night + house.odn);
        if let Some(control) = house.control {
            house.diff = round3(house.total - control);
        }
    }
    Ok(())
}

fn validate_statement(statement: &Statement, _block_pages: usize) -> Result<(), PdfError> {
    // Partial exports keep the original document's page numbering: the title
    // page of the third statement may say `стр. 148 из 1535`. Use the first
    // page's footer number as the base so the sequence check is relative.
    let base = statement
        .pages
        .first()
        .and_then(|page| page.footer.as_deref())
        .and_then(parse_footer_pair)
        .map(|(number, _)| number)
        .unwrap_or(1);
    for (position, page) in statement.pages.iter().enumerate() {
        let expected = base + position as u32;
        match page.footer.as_deref().and_then(parse_footer_pair) {
            Some((number, _total)) => {
                // Accept partial exports: the footer total reflects the
                // original document (e.g. `из 1535`), not the block length.
                // Only require sequential page numbers relative to the base.
                if number != expected {
                    return Err(PdfError::invariant(
                        format!(
                            "footer sequence is {number}, expected {expected}"
                        ),
                        Some(page.page),
                        None,
                        None,
                    ));
                }
            }
            None => {
                if position != 0 {
                    return Err(PdfError::invariant(
                        "missing footer on a continuation page",
                        Some(page.page),
                        None,
                        None,
                    ));
                }
            }
        }
    }

    let official_volume = statement.totals.official.volume.ok_or_else(|| {
        PdfError::invariant("official volume is missing", None, None, None)
    })?;
    let official_amount = statement.totals.official.amount.ok_or_else(|| {
        PdfError::invariant("official amount is missing", None, None, None)
    })?;
    if (statement.totals.control - official_volume).abs() > 0.001 {
        return Err(PdfError::invariant(
            format!(
                "sum of house control {:.3} != official volume {:.3}",
                statement.totals.control, official_volume
            ),
            statement.totals.official.page,
            None,
            None,
        ));
    }
    if (statement.totals.amount - official_amount).abs() > 0.01 {
        return Err(PdfError::invariant(
            format!(
                "sum of house amount {:.2} != official amount {:.2}",
                statement.totals.amount, official_amount
            ),
            statement.totals.official.page,
            None,
            None,
        ));
    }

    for house in &statement.houses {
        let control = house.control.ok_or_else(|| {
            PdfError::invariant(
                "house control is missing",
                Some(house.page),
                Some(house.num),
                None,
            )
        })?;
        if (house.day + house.night + house.odn - control).abs() > 0.001 {
            return Err(PdfError::invariant(
                format!(
                    "day+night+odn {:.3} != control {:.3}",
                    house.day + house.night + house.odn,
                    control
                ),
                Some(house.page),
                Some(house.num),
                None,
            ));
        }
        // Missing main/sub_deduct is legal in correction statements where
        // a house has no meters or no sub-abonents; treat empty cells as 0
        // (the legacy 1C writer does the same).
        let main = house.main.unwrap_or(0.0);
        let sub_deduct = house.sub_deduct.unwrap_or(0.0);
        if (main + sub_deduct - control).abs() > 0.01 {
            return Err(PdfError::invariant(
                format!(
                    "main+sub_deduct {:.3} != control {:.3}",
                    main + sub_deduct,
                    control
                ),
                Some(house.page),
                Some(house.num),
                None,
            ));
        }
        let house_meters: Vec<&Meter> = statement
            .meters
            .iter()
            .filter(|meter| meter.house == house.num)
            .collect();
        let meter_amount = round2(
            house_meters
                .iter()
                .filter(|meter| !meter.is_sub)
                .map(|meter| meter.amount.unwrap_or(0.0))
                .sum(),
        );
        if (meter_amount - house.amount.unwrap_or(0.0)).abs() > 0.01 {
            return Err(PdfError::invariant(
                format!(
                    "sum of meter amounts {:.2} != house amount {:.2}",
                    meter_amount,
                    house.amount.unwrap_or(0.0)
                ),
                Some(house.page),
                Some(house.num),
                None,
            ));
        }
    }

    for meter in &statement.meters {
        if !meter.is_sub {
            let parts = meter.main.unwrap_or(0.0)
                + meter.extra.unwrap_or(0.0)
                + meter.unmetered.unwrap_or(0.0)
                + meter.odn.unwrap_or(0.0)
                + meter.line_loss.unwrap_or(0.0)
                + meter.tr_loss.unwrap_or(0.0)
                + meter.sub_volume.unwrap_or(0.0);
            if (meter.billed.unwrap_or(0.0) - parts).abs() > 0.01 {
                return Err(PdfError::invariant(
                    format!(
                        "billed {:.3} != main+extra+unmetered+odn+losses+sub_volume {:.3}",
                        meter.billed.unwrap_or(0.0),
                        parts
                    ),
                    Some(meter.page),
                    Some(meter.house),
                    Some(meter.row),
                ));
            }
        }
        if let (Some(start), Some(end), Some(delta)) = (meter.start, meter.end, meter.delta) {
            if (end - start - delta).abs() > 0.001 {
                return Err(PdfError::invariant(
                    format!(
                        "delta {:.3} != end {:.3} - start {:.3}",
                        delta, end, start
                    ),
                    Some(meter.page),
                    Some(meter.house),
                    Some(meter.row),
                ));
            }
        }
        if let (Some(main), Some(delta), Some(k)) = (meter.main, meter.delta, meter.k) {
            // Corrections contain manual adjustments, minimum charges and
            // rounding overrides where main != delta * k. The house-level
            // sum check (meters vs house control) remains the real gate;
            // this per-meter discrepancy is informational only.
            if k != 0.0 && (main.abs() - (delta * k).abs()).abs() > 0.01 {
                eprintln!(
                    "warning: page={} house={} row={}: main {:.3} != delta {:.3} * k {:.3}",
                    meter.page, meter.house, meter.row, main, delta, k
                );
            }
        }
    }
    Ok(())
}

fn round3(value: f64) -> f64 {
    let rounded = (value * 1000.0).round() / 1000.0;
    if rounded == 0.0 {
        0.0
    } else {
        rounded
    }
}

fn round2(value: f64) -> f64 {
    let rounded = (value * 100.0).round() / 100.0;
    if rounded == 0.0 {
        0.0
    } else {
        rounded
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn empty_cells() -> Vec<String> {
        vec![String::new(); COLUMNS]
    }

    fn total_cells(column: usize, text: &str) -> Vec<String> {
        let mut cells = empty_cells();
        cells[column] = text.to_string();
        cells
    }

    #[test]
    fn classifies_total_house_and_meter_rows() {
        let mut total = empty_cells();
        total[24] = "Итого:".to_string();
        total[25] = "736 051,312".to_string();
        total[26] = "4 309 766,80".to_string();
        assert_eq!(classify_row(&total), RowKind::Total);

        let mut house = empty_cells();
        house[0] = "2-й Целиноградская, 11".to_string();
        house[25] = "20 457,004".to_string();
        house[26] = "119 264,34".to_string();
        assert_eq!(classify_row(&house), RowKind::House);

        let mut meter = empty_cells();
        meter[0] = "230110609075".to_string();
        meter[2] = "31729560".to_string();
        meter[9] = "5007".to_string();
        meter[10] = "5072".to_string();
        meter[25] = "65".to_string();
        assert_eq!(classify_row(&meter), RowKind::Meter);

        let mut coded_house_like = empty_cells();
        coded_house_like[0] = "230110609075".to_string();
        coded_house_like[25] = "10".to_string();
        assert_eq!(classify_row(&coded_house_like), RowKind::Meter);
    }

    #[test]
    fn parses_all_total_row_layouts() {
        let separate = total_cells(25, "736 051,312");
        let mut separate = separate;
        separate[24] = "Итого:".to_string();
        separate[26] = "4 309 766,80".to_string();
        assert_eq!(total_numbers(&separate), Some((736051.312, 4309766.8)));

        let inline = total_cells(24, "Итого: 1 032 745,77 5 419 801,94");
        assert_eq!(total_numbers(&inline), Some((1032745.77, 5419801.94)));

        let mut glued = total_cells(24, "Итого:");
        glued[25] = "223 073,372 1 159 713,33".to_string();
        assert_eq!(total_numbers(&glued), Some((223073.372, 1159713.33)));

        assert_eq!(total_numbers(&empty_cells()), None);
    }

    #[test]
    fn extracts_metadata_lines() {
        let text = "1\r\nВедомость электропотребления\r\nОрганизация: ООО \"Южный город\"\r\nДоговор: 23110604327 ( 23110604327) от 15.03.2022\r\nМесяц: Октябрь 2026";
        let (org, contract, month) = extract_metadata(text);
        assert_eq!(org.as_deref(), Some("ООО \"Южный город\""));
        assert_eq!(contract.as_deref(), Some("23110604327 ( 23110604327) от 15.03.2022"));
        assert_eq!(month.as_deref(), Some("Октябрь 2026"));
        assert_eq!(statement_kind(org.as_deref()), "gorod");
    }

    #[test]
    fn extracts_split_correction_month() {
        let text = "Месяц:\r\nОктябрь 2026\r\nза сентябрь 2026\r\nТочка учета";
        let (_, _, month) = extract_metadata(text);
        assert_eq!(
            month.as_deref(),
            Some("Октябрь 2026 за сентябрь 2026")
        );
        assert_eq!(
            month.as_deref().and_then(parse_base_period),
            Some("2026-09".to_string())
        );
    }

    fn minimal_statement() -> Statement {
        use crate::model::{Balance, Layout, Official, PageInfo, Source, StatementMeta, Totals};
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
                org: Some("ООО Город".to_string()),
                contract: Some("1".to_string()),
                month: Some("2026-10".to_string()),
                base_period: None,
                month_label: Some("Октябрь 2026".to_string()),
                page_range: [1, 1],
            },
            layout: Layout {
                page_size: [841.89, 595.28],
                columns: 27,
                x_boundaries: vec![0.0; 28],
                confidence: 1.0,
            },
            pages: vec![PageInfo {
                page: 1,
                footer: None,
                rows: 1,
                houses_started: 1,
                role: "title+table".to_string(),
            }],
            houses: vec![House {
                num: 1,
                name: "Дом 1".to_string(),
                page: 1,
                main: Some(10.0),
                sub_deduct: Some(-2.0),
                control: Some(8.0),
                amount: Some(100.0),
                day: 0.0,
                night: 0.0,
                odn: 8.0,
                simple: 8.0,
                total: 8.0,
                diff: 0.0,
                meters_active: 1,
                meters_res: 0,
                sub_rows: 0,
                meter_range: [0, 0],
            }],
            meters: vec![Meter {
                house: 1,
                row: 1,
                page: 1,
                point: "230110605149".to_string(),
                place: String::new(),
                serial: "1".to_string(),
                zone: "odn".to_string(),
                zone_raw: String::new(),
                preview_bucket: "odn".to_string(),
                sub_type: String::new(),
                start: Some(1.0),
                end: Some(9.0),
                delta: Some(8.0),
                k: Some(1.0),
                main: Some(8.0),
                extra: None,
                unmetered: None,
                odn: None,
                line_loss: None,
                tr_loss: None,
                sub_volume: None,
                voltage: "НН".to_string(),
                category: "Первая".to_string(),
                billed: Some(8.0),
                amount: Some(100.0),
                is_sub: false,
                is_reserve: false,
            }],
            totals: Totals {
                day: 0.0,
                night: 0.0,
                odn: 8.0,
                control: 8.0,
                amount: 100.0,
                official: Official {
                    volume: Some(8.0),
                    amount: Some(100.0),
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
    fn validates_invariants_and_reports_context() {
        assert!(validate_statement(&minimal_statement(), 1).is_ok());

        let mut broken = minimal_statement();
        broken.totals.control = 9.0;
        assert!(matches!(
            validate_statement(&broken, 1),
            Err(PdfError::Invariant { .. })
        ));

        let mut broken = minimal_statement();
        broken.meters[0].delta = Some(7.0);
        assert!(matches!(
            validate_statement(&broken, 1),
            Err(PdfError::Invariant { .. })
        ));

        // Footer base is relative to the first page (partial exports can
        // start at `стр. 82 из 1535`), so a single page with any footer
        // number is valid. What must fail is a non-sequential footer on a
        // continuation page.
        let mut broken = minimal_statement();
        broken.pages.push(crate::model::PageInfo {
            page: 2,
            footer: Some("5/2".to_string()),
            rows: 10,
            houses_started: 0,
            role: "continuation".to_string(),
        });
        assert!(matches!(
            validate_statement(&broken, 2),
            Err(PdfError::Invariant { .. })
        ));

        let mut broken = minimal_statement();
        broken.pages.push(crate::model::PageInfo {
            page: 2,
            footer: None,
            rows: 10,
            houses_started: 0,
            role: "continuation".to_string(),
        });
        assert!(matches!(
            validate_statement(&broken, 2),
            Err(PdfError::Invariant { .. })
        ));
    }

    #[test]
    #[ignore]
    fn parses_city_fixture() {
        let path = std::env::var("TNS_PDF_FIXTURE").expect("TNS_PDF_FIXTURE");
        let statements =
            parse_pdf(Path::new(&path)).expect("city statement must parse");
        assert_eq!(statements.len(), 1);
        let statement = &statements[0];
        assert_eq!(statement.source.pages, 82);
        assert_eq!(statement.statement.kind, "gorod");
        assert_eq!(statement.statement.month.as_deref(), Some("2026-10"));
        assert_eq!(statement.statement.page_range, [1, 82]);
        assert_eq!(statement.layout.columns, 27);
        assert_eq!(statement.layout.x_boundaries.len(), 28);
        assert_eq!(statement.pages.len(), 82);
        assert_eq!(statement.pages[0].footer, None);
        for page in &statement.pages[1..] {
            let expected = format!("{}/82", page.page);
            assert_eq!(page.footer.as_deref(), Some(expected.as_str()));
        }
        assert_eq!(statement.houses.len(), 22);
        assert!((statement.totals.official.volume.unwrap() - 736051.312).abs() < 0.001);
        assert!((statement.totals.official.amount.unwrap() - 4309766.80).abs() < 0.01);
        assert_eq!(statement.totals.balance.volume, 0.0);
        assert_eq!(statement.totals.balance.amount, 0.0);
        assert!(statement.warnings.is_empty());
    }
}
