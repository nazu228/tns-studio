//! Output workbook styles, conditional formatting and hyperlinks.
//!
//! Ports the styling part of legacy `core_engine.process_statement`: the
//! calculation block AD..AL on the statement sheet, the summary dashboard
//! cells, the deviation conditional formatting and the address hyperlinks.
//! Styles are applied after the slice-1 writer has placed values, formulas,
//! merges, freeze panes and dimensions, in the legacy assignment order.

use crate::process::{billed_value, House};
use crate::{column_letter, LayoutColumns, TnsError};
use tns_excel::{
    Alignment, Border, Color, ConditionalFormatValues, ConditionalFormatting,
    ConditionalFormattingOperatorValues, ConditionalFormattingRule, Fill, Font, Formula,
    HorizontalAlignmentValues, Hyperlink, NumberingFormat, PatternValues, Style,
    VerticalAlignmentValues, Worksheet,
};

const FONT_FAMILY: &str = "Segoe UI";
const NUM_FMT_VOL: &str = "#,##0.000";
const STATEMENT_TITLE: &str = "Ведомость ЭП";

const FILL_DAY: &str = "FFF2CC";
const FILL_NIGHT: &str = "D9E1F2";
const FILL_ODN: &str = "E2EFDA";
const FILL_SUB: &str = "F2F2F2";
const FILL_HOUSE_HEADER: &str = "BDD7EE";
const FILL_CALC_ROW: &str = "F2F4F7";
const FILL_TOTAL_ROW: &str = "D9E1F2";
const FILL_GREEN: &str = "E2EFDA";
const FILL_RED: &str = "FFCDD2";

const COLOR_GREEN: &str = "1E7E34";
const COLOR_RED: &str = "B71C1C";

const BORDER_COLOR: &str = "D3D3D3";
const TOTAL_BORDER_COLOR: &str = "1F4E79";

fn argb(hex: &str) -> String {
    format!("00{}", hex)
}

fn font(size: f64, bold: bool, italic: bool, color: Option<&str>) -> Font {
    let mut font = Font::default();
    font.set_name(FONT_FAMILY);
    font.set_size(size);
    if bold {
        font.set_bold(true);
    }
    if italic {
        font.set_italic(true);
    }
    if let Some(color) = color {
        font.color_mut().set_argb_str(argb(color));
    }
    font
}

fn solid_fill(hex: &str) -> Fill {
    let mut fill = Fill::default();
    let pattern = fill.pattern_fill_mut();
    pattern.set_pattern_type(PatternValues::Solid);
    pattern.foreground_color_mut().set_argb_str(argb(hex));
    pattern.background_color_mut().set_argb_str(argb(hex));
    fill
}

fn set_side(border: &mut Border, style: &str, hex: &str) {
    border.set_border_style(style);
    let mut color = Color::default();
    color.set_argb_str(argb(hex));
    border.set_color(color);
}

fn apply_box_border(style: &mut Style) {
    let borders = style.borders_mut();
    set_side(borders.left_mut(), "thin", BORDER_COLOR);
    set_side(borders.right_mut(), "thin", BORDER_COLOR);
    set_side(borders.top_mut(), "thin", BORDER_COLOR);
    set_side(borders.bottom_mut(), "thin", BORDER_COLOR);
}

fn apply_total_border(style: &mut Style) {
    let borders = style.borders_mut();
    set_side(borders.left_mut(), "thin", BORDER_COLOR);
    set_side(borders.right_mut(), "thin", BORDER_COLOR);
    set_side(borders.top_mut(), "thin", BORDER_COLOR);
    set_side(borders.bottom_mut(), "double", TOTAL_BORDER_COLOR);
}

fn alignment(horizontal: HorizontalAlignmentValues, vertical: VerticalAlignmentValues) -> Alignment {
    let mut alignment = Alignment::default();
    alignment.set_horizontal(horizontal);
    alignment.set_vertical(vertical);
    alignment
}

fn aligned(
    horizontal: HorizontalAlignmentValues,
    vertical: VerticalAlignmentValues,
    wrap: bool,
) -> Alignment {
    let mut alignment = alignment(horizontal, vertical);
    alignment.set_wrap_text(wrap);
    alignment
}

fn volume_format() -> NumberingFormat {
    let mut format = NumberingFormat::default();
    format.set_format_code(NUM_FMT_VOL);
    format
}

fn meter_style(sheet: &mut Worksheet, row: usize, fill: &str, bold: bool, col_cat: usize) {
    let style = sheet.style_mut((col_cat as u32, row as u32));
    style.set_fill(solid_fill(fill));
    style.set_font(font(9.0, bold, false, None));
}

/// Style the statement calculation block (columns AD..AL).
///
/// Assignment order mirrors legacy: the global header row first, then the
/// meter rows (which overwrite AD10/AE10), then the house headers. A house
/// day meter on row 10 therefore keeps the day fill/font while keeping the
/// header alignment from the first pass.
pub(crate) fn style_statement(
    sheet: &mut Worksheet,
    col_start: usize,
    columns: &LayoutColumns,
    houses: &[House],
    statement_total_row: usize,
) -> Result<(), TnsError> {
    let col_cat = col_start;
    let col_stat = col_start + 1;
    let col_day = col_start + 2;
    let col_diff = col_start + 7;
    let col_audit = col_start + 8;

    // Global header row (legacy writes row 10 before the houses).
    for column in col_cat..=col_audit {
        let style = sheet.style_mut((column as u32, 10));
        style.set_font(font(9.0, true, false, Some("FFFFFF")));
        style.set_fill(solid_fill("1F4E79"));
        style.set_alignment(aligned(
            HorizontalAlignmentValues::Center,
            VerticalAlignmentValues::Center,
            true,
        ));
    }

    for house in houses {
        for row in &house.day_rows {
            let active = billed_value(sheet, *row, columns.col_billed_vol)? > 0.0;
            meter_style(sheet, *row, FILL_DAY, true, col_cat);
            let style = sheet.style_mut((col_stat as u32, *row as u32));
            style.set_font(font(9.0, active, false, None));
        }
        for row in &house.night_rows {
            let active = billed_value(sheet, *row, columns.col_billed_vol)? > 0.0;
            meter_style(sheet, *row, FILL_NIGHT, true, col_cat);
            let style = sheet.style_mut((col_stat as u32, *row as u32));
            style.set_font(font(9.0, active, false, None));
        }
        for row in &house.odn_rows {
            let active = billed_value(sheet, *row, columns.col_billed_vol)? > 0.0;
            meter_style(sheet, *row, FILL_ODN, true, col_cat);
            let style = sheet.style_mut((col_stat as u32, *row as u32));
            style.set_font(font(9.0, active, false, None));
        }
        for row in &house.sub_rows {
            meter_style(sheet, *row, FILL_SUB, false, col_cat);
            let style = sheet.style_mut((col_stat as u32, *row as u32));
            style.set_font(font(9.0, false, false, None));
        }
    }

    for house in houses {
        let header = house.header_row;
        let style = sheet.style_mut((col_cat as u32, header as u32));
        style.set_fill(solid_fill(FILL_HOUSE_HEADER));
        style.set_font(font(9.0, true, false, None));

        let style = sheet.style_mut((col_stat as u32, header as u32));
        style.set_font(font(9.0, true, false, None));

        for column in col_day..=col_diff {
            let style = sheet.style_mut((column as u32, header as u32));
            style.set_number_format(volume_format());
            style.set_font(font(10.0, true, false, None));
            style.set_fill(solid_fill(FILL_CALC_ROW));
            apply_box_border(style);
        }

        let style = sheet.style_mut((col_audit as u32, header as u32));
        style.set_font(font(9.0, true, false, Some(COLOR_GREEN)));
        style.set_fill(solid_fill(FILL_GREEN));
        apply_box_border(style);
    }

    let style = sheet.style_mut((col_cat as u32, statement_total_row as u32));
    style.set_font(font(10.0, true, false, None));
    style.set_fill(solid_fill(FILL_TOTAL_ROW));

    for column in col_day..=col_diff {
        let style = sheet.style_mut((column as u32, statement_total_row as u32));
        style.set_number_format(volume_format());
        style.set_font(font(10.0, true, false, None));
        style.set_fill(solid_fill(FILL_TOTAL_ROW));
        apply_total_border(style);
    }

    let style = sheet.style_mut((col_audit as u32, statement_total_row as u32));
    style.set_font(font(9.0, true, false, Some(COLOR_GREEN)));
    style.set_fill(solid_fill(FILL_GREEN));
    apply_total_border(style);

    Ok(())
}

fn conditional_rule(
    operator: ConditionalFormattingOperatorValues,
    priority: i32,
    fill: &str,
    font_color: &str,
) -> ConditionalFormattingRule {
    let mut rule = ConditionalFormattingRule::default();
    rule.set_type(ConditionalFormatValues::CellIs);
    rule.set_operator(operator);
    rule.set_priority(priority);
    rule.set_stop_if_true(true);
    let mut formula = Formula::default();
    formula.set_string_value("0");
    rule.set_formula(formula);

    let mut style = Style::default();
    style.set_font(font(9.0, true, false, Some(font_color)));
    style.set_fill(solid_fill(fill));
    rule.set_style(style);
    rule
}

fn deviation_formatting(total_row: usize) -> ConditionalFormatting {
    let mut formatting = ConditionalFormatting::default();
    formatting
        .sequence_of_references_mut()
        .set_sqref(format!("H6:H{}", total_row));
    formatting.add_conditional_collection(conditional_rule(
        ConditionalFormattingOperatorValues::Equal,
        1,
        FILL_GREEN,
        COLOR_GREEN,
    ));
    formatting.add_conditional_collection(conditional_rule(
        ConditionalFormattingOperatorValues::NotEqual,
        2,
        FILL_RED,
        COLOR_RED,
    ));
    formatting
}

/// Style the summary dashboard, add the deviation hyperlinks and CF.
pub(crate) fn style_summary(sheet: &mut Worksheet, col_start: usize, houses: &[House]) {
    let day_letter = column_letter(col_start + 2);

    let style = sheet.style_mut("A1");
    style.set_font(font(13.0, true, false, Some("1F4E79")));
    style.set_alignment(alignment(
        HorizontalAlignmentValues::Left,
        VerticalAlignmentValues::Center,
    ));

    let style = sheet.style_mut("A2");
    style.set_font(font(9.0, false, true, Some("555555")));
    style.set_alignment(alignment(
        HorizontalAlignmentValues::Left,
        VerticalAlignmentValues::Center,
    ));

    let style = sheet.style_mut("A3");
    style.set_font(font(9.0, true, false, Some(COLOR_GREEN)));
    style.set_fill(solid_fill(FILL_GREEN));
    style.set_alignment(alignment(
        HorizontalAlignmentValues::Left,
        VerticalAlignmentValues::Center,
    ));

    for column in 1..=10u32 {
        let style = sheet.style_mut((column, 5));
        style.set_font(font(9.0, true, false, Some("FFFFFF")));
        style.set_fill(solid_fill("1F4E79"));
        style.set_alignment(aligned(
            HorizontalAlignmentValues::Center,
            VerticalAlignmentValues::Center,
            true,
        ));
        apply_box_border(style);
    }

    for (index, house) in houses.iter().enumerate() {
        let row = (6 + index) as u32;
        let header_row = house.header_row;

        let style = sheet.style_mut((1u32, row));
        style.set_alignment(alignment(
            HorizontalAlignmentValues::Center,
            VerticalAlignmentValues::Center,
        ));

        let style = sheet.style_mut((2u32, row));
        style.set_font(font(10.0, true, false, Some("0D6EFD")));
        style.set_alignment(alignment(
            HorizontalAlignmentValues::Left,
            VerticalAlignmentValues::Center,
        ));
        let mut link = Hyperlink::default();
        link.set_url(format!(
            "#'{}'!{}{}",
            STATEMENT_TITLE, day_letter, header_row
        ));
        sheet.cell_mut((2u32, row)).set_hyperlink(link);

        for (column, fill) in [(3u32, FILL_DAY), (4u32, FILL_NIGHT), (5u32, FILL_ODN)] {
            let style = sheet.style_mut((column, row));
            style.set_fill(solid_fill(fill));
        }

        let style = sheet.style_mut((6u32, row));
        style.set_font(font(10.0, true, false, None));

        let style = sheet.style_mut((8u32, row));
        style.set_font(font(10.0, true, false, None));

        let style = sheet.style_mut((9u32, row));
        style.set_font(font(9.0, false, false, Some("555555")));
        style.set_alignment(alignment(
            HorizontalAlignmentValues::Center,
            VerticalAlignmentValues::Center,
        ));

        let style = sheet.style_mut((10u32, row));
        style.set_font(font(9.0, false, false, Some("333333")));
        style.set_alignment(alignment(
            HorizontalAlignmentValues::Center,
            VerticalAlignmentValues::Center,
        ));

        for column in 1..=10u32 {
            let style = sheet.style_mut((column, row));
            if (3..=8).contains(&column) {
                style.set_number_format(volume_format());
                style.set_alignment(alignment(
                    HorizontalAlignmentValues::Right,
                    VerticalAlignmentValues::Center,
                ));
            }
            apply_box_border(style);
        }
    }

    let total_row = 6 + houses.len();
    let total_row_u32 = total_row as u32;

    let style = sheet.style_mut((2u32, total_row_u32));
    style.set_alignment(alignment(
        HorizontalAlignmentValues::Right,
        VerticalAlignmentValues::Center,
    ));

    for column in 1..=10u32 {
        // Legacy creates A/I/J through cell(tot_dr, col) even though they stay empty.
        sheet.cell_mut((column, total_row_u32));
        let style = sheet.style_mut((column, total_row_u32));
        style.set_font(font(10.0, true, false, None));
        style.set_fill(solid_fill(FILL_TOTAL_ROW));
        apply_total_border(style);
        if (3..=8).contains(&column) {
            style.set_number_format(volume_format());
            style.set_alignment(alignment(
                HorizontalAlignmentValues::Right,
                VerticalAlignmentValues::Center,
            ));
        }
    }

    sheet.add_conditional_formatting_collection(deviation_formatting(total_row));
}
