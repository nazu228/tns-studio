//! Output workbook writer, slice 1.
//!
//! Ports the calculation columns and the summary dashboard of legacy
//! `core_engine.process_statement`: values, formulas, merges, freeze panes and
//! dimensions. Styles, conditional formatting and hyperlinks are slice 2.

use crate::process::{billed_value, House};
use crate::{column_letter, LayoutColumns, TnsError};
use tns_excel::{Workbook, Worksheet};

const STATEMENT_TITLE: &str = "Ведомость ЭП";
const SUMMARY_TITLE: &str = "Сводка по домам";

const STATUS_ACTIVE: &str = "В работе (с расходом)";
const STATUS_RESERVE: &str = "⚪ Резерв (0 кВт*ч, АВР-2)";

pub(crate) struct HouseStats {
    min_row: usize,
    max_row: usize,
    meters: usize,
    active: usize,
    reserve: usize,
}

pub(crate) struct StatementLayout {
    col_start: usize,
    stats: Vec<HouseStats>,
}

fn cell_text(sheet: &mut Worksheet, column: usize, row: usize, value: &str) {
    // umya tuple coordinates are (column, row), unlike A1 strings.
    sheet
        .cell_mut((column as u32, row as u32))
        .set_value_string(value);
}

fn cell_number(sheet: &mut Worksheet, column: usize, row: usize, value: f64) {
    sheet
        .cell_mut((column as u32, row as u32))
        .set_value_number(value);
}

fn cell_formula(sheet: &mut Worksheet, column: usize, row: usize, value: String) {
    // umya stores formulas without the leading '='.
    sheet
        .cell_mut((column as u32, row as u32))
        .set_formula(value);
}

fn sum_formula(rows: &[usize], billed_letter: &str) -> Option<String> {
    if rows.is_empty() {
        return None;
    }
    let refs: Vec<String> = rows
        .iter()
        .map(|row| format!("{}{}", billed_letter, row))
        .collect();
    Some(format!("SUM({})", refs.join(", ")))
}

fn status_text(active: bool) -> &'static str {
    if active {
        STATUS_ACTIVE
    } else {
        STATUS_RESERVE
    }
}

fn set_column_widths(sheet: &mut Worksheet, widths: &[(usize, f64)]) {
    let mut previous: Option<f64> = None;
    for (column, width) in widths {
        // shortcut: umya coalesces adjacent <col> entries with equal width, and
        // openpyxl exposes such a range as one dimension. A 1e-7 nudge keeps
        // columns separate while openpyxl rounds widths to 6 decimals, so the
        // signature still reads 18.0/22.0/24.0. Revisit when umya writes one
        // <col> per column.
        let width = match previous {
            Some(previous) if previous == *width => *width + 1e-7,
            _ => *width,
        };
        sheet
            .column_dimension_mut(&column_letter(*column))
            .set_width(width);
        previous = Some(width);
    }
}

fn open_statement(book: &mut Workbook) -> Result<&mut Worksheet, TnsError> {
    book.sheet_mut(0)
        .map_err(|error| TnsError::Message(format!("Не удалось открыть лист: {}", error)))
}

/// Rename the source sheet and add the calculation block AD..AL.
pub(crate) fn write_statement(
    book: &mut Workbook,
    columns: &LayoutColumns,
    houses: &[House],
    statement_total_row: usize,
) -> Result<StatementLayout, TnsError> {
    let col_start = {
        let sheet = book
            .sheet(0)
            .map_err(|error| TnsError::Message(format!("Не удалось открыть лист: {}", error)))?;
        (sheet.highest_column() as usize + 2).max(30)
    };

    // Statuses are read before mutating the book; legacy reads billed_value
    // again while marking the rows.
    let active: Vec<Vec<bool>> = {
        let sheet = book
            .sheet(0)
            .map_err(|error| TnsError::Message(format!("Не удалось открыть лист: {}", error)))?;
        let mut result = Vec::with_capacity(houses.len());
        for house in houses {
            let mut flags = Vec::new();
            for row in house.all_meter_rows() {
                flags.push(billed_value(sheet, row, columns.col_billed_vol)? > 0.0);
            }
            result.push(flags);
        }
        result
    };

    let col_cat = col_start;
    let col_stat = col_start + 1;
    let col_day = col_start + 2;
    let col_night = col_start + 3;
    let col_odn = col_start + 4;
    let col_tot = col_start + 5;
    let col_ctrl = col_start + 6;
    let col_diff = col_start + 7;
    let col_audit = col_start + 8;

    let billed_letter = column_letter(columns.col_billed_vol);
    let day_letter = column_letter(col_day);
    let night_letter = column_letter(col_night);
    let odn_letter = column_letter(col_odn);
    let tot_letter = column_letter(col_tot);
    let ctrl_letter = column_letter(col_ctrl);
    let diff_letter = column_letter(col_diff);

    let statement = open_statement(book)?;
    statement.set_name(STATEMENT_TITLE);

    for (column, value) in [
        (col_cat, "Категория для начисления"),
        (col_stat, "Статус прибора учета"),
        (col_day, "⚡ Энергия День (кВт*ч)"),
        (col_night, "🌙 Энергия Ночь (кВт*ч)"),
        (col_odn, "💡 ОДН (кВт*ч)"),
        (col_tot, "ИТОГО по формулам (кВт*ч)"),
        (col_ctrl, "Контроль ТНС (кВт*ч)"),
        (col_diff, "Отклонение (кВт*ч)"),
        (col_audit, "Аудит баланса"),
    ] {
        cell_text(statement, column, 10, value);
    }

    let mut stats = Vec::with_capacity(houses.len());
    for (index, house) in houses.iter().enumerate() {
        let (day_flags, rest) = active[index].split_at(house.day_rows.len());
        let (night_flags, odn_flags) = rest.split_at(house.night_rows.len());

        for (row, active) in house.day_rows.iter().zip(day_flags) {
            cell_text(statement, col_cat, *row, "⚡ День");
            cell_text(statement, col_stat, *row, status_text(*active));
        }
        for (row, active) in house.night_rows.iter().zip(night_flags) {
            cell_text(statement, col_cat, *row, "🌙 Ночь");
            cell_text(statement, col_stat, *row, status_text(*active));
        }
        for (row, active) in house.odn_rows.iter().zip(odn_flags) {
            cell_text(statement, col_cat, *row, "💡 ОДН");
            cell_text(statement, col_stat, *row, status_text(*active));
        }
        for row in &house.sub_rows {
            cell_text(statement, col_cat, *row, "🛡️ Субабонент");
            cell_text(statement, col_stat, *row, "Вычтен ТНС (не включен)");
        }

        // Legacy writes row-10 headers before the meters, so the day meter at
        // row 10 overwrites AD10/AE10 in the golden workbook.
        let header_row = house.header_row;
        let all_meters = house.all_meter_rows();
        cell_text(statement, col_cat, header_row, "ДОМ / ОБЪЕКТ");
        cell_text(
            statement,
            col_stat,
            header_row,
            &format!("{} ПУ", all_meters.len()),
        );

        match sum_formula(&house.day_rows, &billed_letter) {
            Some(formula) => cell_formula(statement, col_day, header_row, formula),
            None => cell_number(statement, col_day, header_row, 0.0),
        }
        match sum_formula(&house.night_rows, &billed_letter) {
            Some(formula) => cell_formula(statement, col_night, header_row, formula),
            None => cell_number(statement, col_night, header_row, 0.0),
        }
        match sum_formula(&house.odn_rows, &billed_letter) {
            Some(formula) => cell_formula(statement, col_odn, header_row, formula),
            None => cell_number(statement, col_odn, header_row, 0.0),
        }

        let mut ai = String::new();
        ai.push_str(&format!("{}{}+", day_letter, header_row));
        ai.push_str(&format!("{}{}+", night_letter, header_row));
        ai.push_str(&format!("{}{}", odn_letter, header_row));
        cell_formula(statement, col_tot, header_row, ai);
        cell_formula(
            statement,
            col_ctrl,
            header_row,
            format!("{}{}", billed_letter, header_row),
        );
        cell_formula(
            statement,
            col_diff,
            header_row,
            format!("ROUND({}{}-{}{}, 3)", tot_letter, header_row, ctrl_letter, header_row),
        );
        cell_formula(
            statement,
            col_audit,
            header_row,
            format!(
                "IF({}{}=0, \"✔ Сошлось\", \"❌ Ошибка\")",
                diff_letter, header_row
            ),
        );

        let reserve = all_meters
            .iter()
            .zip(&active[index])
            .filter(|(_, active)| !**active)
            .count();
        stats.push(HouseStats {
            min_row: all_meters.iter().copied().min().unwrap_or(header_row),
            max_row: all_meters.iter().copied().max().unwrap_or(header_row),
            meters: all_meters.len(),
            active: all_meters.len() - reserve,
            reserve,
        });
    }

    let first_header = houses[0].header_row;
    let last_header = houses[houses.len() - 1].header_row;
    cell_text(
        statement,
        col_cat,
        statement_total_row,
        "ИТОГО ПО ВЕДОМОСТИ",
    );
    for (letter, column) in [
        (day_letter.as_str(), col_day),
        (night_letter.as_str(), col_night),
        (odn_letter.as_str(), col_odn),
        (tot_letter.as_str(), col_tot),
    ] {
        cell_formula(
            statement,
            column,
            statement_total_row,
            format!("SUM({}{}:{}{})", letter, first_header, letter, last_header),
        );
    }
    cell_formula(
        statement,
        col_ctrl,
        statement_total_row,
        format!("{}{}", billed_letter, statement_total_row),
    );
    cell_formula(
        statement,
        col_diff,
        statement_total_row,
        format!(
            "ROUND({}{}-{}{}, 3)",
            tot_letter, statement_total_row, ctrl_letter, statement_total_row
        ),
    );
    cell_formula(
        statement,
        col_audit,
        statement_total_row,
        format!(
            "IF({}{}=0, \"✔ 100% БАЛАНС\", \"❌ ОШИБКА\")",
            diff_letter, statement_total_row
        ),
    );

    set_column_widths(
        statement,
        &[
            (col_cat, 24.0),
            (col_stat, 28.0),
            (col_day, 18.0),
            (col_night, 18.0),
            (col_odn, 18.0),
            (col_tot, 22.0),
            (col_ctrl, 22.0),
            (col_diff, 16.0),
            (col_audit, 18.0),
        ],
    );

    crate::output_style::style_statement(
        statement,
        col_start,
        columns,
        houses,
        statement_total_row,
    )?;

    Ok(StatementLayout { col_start, stats })
}

fn set_frozen_at_c6(sheet: &mut Worksheet) {
    // umya exposes the pane mutators but not the pane enum types through
    // tns-excel, so the enums are built from their XML names.
    fn enum_value<T: std::str::FromStr>(value: &str) -> T {
        match value.parse() {
            Ok(parsed) => parsed,
            Err(_) => unreachable!("invalid umya enum value"),
        }
    }

    let views = sheet.sheet_views_mut();
    if views.sheet_view_list().is_empty() {
        views.add_sheet_view_list_mut(Default::default());
    }
    let view = &mut views.sheet_view_list_mut()[0];
    view.set_pane(Default::default());
    let pane = view.pane_mut().expect("pane");
    pane.set_horizontal_split(2.0);
    pane.set_vertical_split(5.0);
    pane.top_left_cell_mut().set_coordinate("C6");
    pane.set_active_pane(enum_value("bottomRight"));
    pane.set_state(enum_value("frozen"));
}

/// Create the summary dashboard at index 0 and move the statement to index 1.
pub(crate) fn write_summary(
    book: &mut Workbook,
    columns: &LayoutColumns,
    layout: &StatementLayout,
    houses: &[House],
    statement_total_row: usize,
    consumer: &str,
    contract: &str,
    period: &str,
) -> Result<(), TnsError> {
    let col_start = layout.col_start;
    let billed_letter = column_letter(columns.col_billed_vol);
    let house_letter = column_letter(columns.col_house_name);
    let day_letter = column_letter(col_start + 2);
    let night_letter = column_letter(col_start + 3);
    let odn_letter = column_letter(col_start + 4);

    let summary = book.new_sheet(SUMMARY_TITLE).map_err(|error| {
        TnsError::Message(format!("Не удалось создать лист «{}»: {}", SUMMARY_TITLE, error))
    })?;

    summary.add_merge_cells("A1:J1");
    summary.add_merge_cells("A2:J2");
    summary.add_merge_cells("A3:J3");
    set_frozen_at_c6(summary);

    cell_text(
        summary,
        1,
        1,
        &format!(
            "СВОДНАЯ ВЕДОМОСТЬ НАЧИСЛЕНИЙ ЭЛЕКТРОЭНЕРГИИ — {}",
            consumer.to_uppercase()
        ),
    );
    summary.row_dimension_mut(1).set_height(24.0);
    cell_text(
        summary,
        1,
        2,
        &format!(
            "Месяц: {} | Договор: {} | Источник: Ведомость ТНС Энерго | Контроль: столбец AB",
            period, contract
        ),
    );
    summary.row_dimension_mut(2).set_height(18.0);
    cell_text(
        summary,
        1,
        3,
        "✔ Все формулы расчета размещены на листе «Ведомость ЭП». Ячейки сводки ссылаются прямо на расчетные формулы.",
    );
    summary.row_dimension_mut(3).set_height(20.0);

    for (column, value) in [
        (1, "№"),
        (2, "Адрес дома (Объект)"),
        (3, "⚡ Энергия День (кВт*ч)"),
        (4, "🌙 Энергия Ночь (кВт*ч)"),
        (5, "💡 ОДН (кВт*ч)"),
        (6, "ИТОГО начислено (кВт*ч)"),
        (7, "Контроль ведомость (ст. AB)"),
        (8, "Отклонение (кВт*ч)"),
        (9, "Строки ведомости"),
        (10, "Кол-во ПУ"),
    ] {
        cell_text(summary, column, 5, value);
    }
    summary.row_dimension_mut(5).set_height(28.0);

    for (index, (house, stats)) in houses.iter().zip(&layout.stats).enumerate() {
        let row = 6 + index;
        let header_row = house.header_row;
        summary.row_dimension_mut(row as u32).set_height(22.0);
        cell_number(summary, 1, row, (index + 1) as f64);
        cell_formula(
            summary,
            2,
            row,
            format!("'{}'!{}{}", STATEMENT_TITLE, house_letter, header_row),
        );
        for (column, letter) in [
            (3, day_letter.as_str()),
            (4, night_letter.as_str()),
            (5, odn_letter.as_str()),
        ] {
            cell_formula(
                summary,
                column,
                row,
                format!("'{}'!{}{}", STATEMENT_TITLE, letter, header_row),
            );
        }
        cell_formula(summary, 6, row, format!("C{}+D{}+E{}", row, row, row));
        cell_formula(
            summary,
            7,
            row,
            format!("'{}'!{}{}", STATEMENT_TITLE, billed_letter, header_row),
        );
        cell_formula(summary, 8, row, format!("ROUND(F{}-G{}, 3)", row, row));
        cell_text(
            summary,
            9,
            row,
            &format!("стр. {} – {}", stats.min_row, stats.max_row),
        );
        cell_text(
            summary,
            10,
            row,
            &format!(
                "{} ПУ ({} раб. / {} рез.)",
                stats.meters, stats.active, stats.reserve
            ),
        );
    }

    let total_row = 6 + houses.len();
    summary.row_dimension_mut(total_row as u32).set_height(24.0);
    cell_text(summary, 2, total_row, "ИТОГО ПО ВСЕМ ДОМАМ:");
    for column in 3..=6 {
        let letter = column_letter(column);
        cell_formula(
            summary,
            column,
            total_row,
            format!("SUM({}6:{}{})", letter, letter, total_row - 1),
        );
    }
    cell_formula(
        summary,
        7,
        total_row,
        format!("'{}'!{}{}", STATEMENT_TITLE, billed_letter, statement_total_row),
    );
    cell_formula(
        summary,
        8,
        total_row,
        format!("ROUND(F{}-G{}, 3)", total_row, total_row),
    );

    set_column_widths(
        summary,
        &[
            (1, 6.0),
            (2, 38.0),
            (3, 22.0),
            (4, 22.0),
            (5, 22.0),
            (6, 24.0),
            (7, 24.0),
            (8, 18.0),
            (9, 22.0),
            (10, 24.0),
        ],
    );

    crate::output_style::style_summary(summary, col_start, houses);

    // Summary is created at the end; legacy inserts it at index 0. Rotate
    // instead of swap so extra source sheets keep their relative order.
    book.sheet_collection_mut().rotate_right(1);
    Ok(())
}
