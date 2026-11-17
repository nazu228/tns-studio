"""Tests for the independent xlsx signature used as the parity oracle.

These tests do not run legacy or Rust code. They prove that the verifier sees
the workbook features the port must reproduce: sheet order, conditional
formatting styles, hyperlinks, hidden rows/columns, defined names and
validations.
"""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from parity_lib import xlsx_signature


def _make_workbook(path, sheet_names=("Second", "First"), fill_color="FFF2CC"):
    workbook = Workbook()
    workbook.active.title = sheet_names[0]
    for name in sheet_names[1:]:
        workbook.create_sheet(name)

    sheet = workbook["Second"]
    sheet["A1"] = "Report"
    sheet["A1"].font = Font(name="Segoe UI", size=13, bold=True, color="1F4E79")
    sheet.merge_cells("A1:B1")
    sheet.freeze_panes = "C6"

    sheet.column_dimensions["D"].width = 18.5
    sheet.column_dimensions["E"].hidden = True
    sheet.row_dimensions[2].height = 24.0
    sheet.row_dimensions[3].hidden = True

    sheet["A2"] = 0
    sheet["A2"].number_format = "#,##0.000"
    sheet["B2"] = "link"
    sheet["B2"].hyperlink = "https://example.com"
    sheet["C1"] = 1
    sheet["C1"].border = Border(left=Side(style="thin", color="D3D3D3"))
    sheet["C1"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Styled empty cells are part of the visual contract too.
    sheet["A5"].fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    sheet.conditional_formatting.add(
        "A2:A10",
        CellIsRule(
            operator="equal",
            formula=["0"],
            stopIfTrue=True,
            fill=PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid"),
            font=Font(color="1E7E34", bold=True),
        ),
    )

    validation = DataValidation(type="list", formula1='"A,B"', allow_blank=True)
    sheet.add_data_validation(validation)
    validation.add("D1:D3")

    workbook.defined_names["MyName"] = DefinedName("MyName", attr_text="'Second'!$A$1")
    workbook.save(path)


def test_signature_tracks_sheet_order(tmp_path):
    first = tmp_path / "first.xlsx"
    second = tmp_path / "second.xlsx"
    _make_workbook(first, ("Second", "First"))
    _make_workbook(second, ("First", "Second"))

    left = xlsx_signature(first)
    right = xlsx_signature(second)

    assert left["sheet_order"] == ["Second", "First"]
    assert right["sheet_order"] == ["First", "Second"]
    assert left["sheets"]["Second"]["index"] == 0
    assert right["sheets"]["Second"]["index"] == 1
    assert left != right


def test_signature_captures_conditional_formatting(tmp_path):
    path = tmp_path / "cf.xlsx"
    _make_workbook(path)
    signature = xlsx_signature(path)

    rules = signature["sheets"]["Second"]["conditional_formatting"]
    assert len(rules) == 1
    assert rules[0]["range"] == "A2:A10"

    rule = rules[0]["rules"][0]
    assert rule["type"] == "cellIs"
    assert rule["operator"] == "equal"
    assert rule["formula"] == ["0"]
    assert rule["priority"] == 1
    assert rule["stopIfTrue"] is True
    assert rule["dxf"]["fill"]["fgColor"]["rgb"].endswith("FFF2CC")
    assert rule["dxf"]["font"]["bold"] is True
    assert rule["dxf"]["font"]["color"]["rgb"].endswith("1E7E34")


def test_signature_distinguishes_conditional_formatting_style(tmp_path):
    yellow = tmp_path / "yellow.xlsx"
    green = tmp_path / "green.xlsx"
    _make_workbook(yellow, fill_color="FFF2CC")
    _make_workbook(green, fill_color="E2EFDA")

    yellow_rule = xlsx_signature(yellow)["sheets"]["Second"]["conditional_formatting"][0]["rules"][0]
    green_rule = xlsx_signature(green)["sheets"]["Second"]["conditional_formatting"][0]["rules"][0]

    assert yellow_rule["formula"] == green_rule["formula"]
    assert yellow_rule["dxf"] != green_rule["dxf"]


def test_signature_captures_links_hidden_dimensions_and_names(tmp_path):
    path = tmp_path / "features.xlsx"
    _make_workbook(path)
    signature = xlsx_signature(path)
    sheet = signature["sheets"]["Second"]

    assert sheet["state"] == "visible"
    assert sheet["freeze_panes"] == "C6"
    assert "A1:B1" in sheet["merged"]
    assert sheet["col_widths"]["D"]["width"] == 18.5
    assert sheet["col_widths"]["E"]["hidden"] is True
    assert sheet["row_heights"]["2"]["height"] == 24.0
    assert sheet["row_heights"]["3"]["hidden"] is True
    assert sheet["cells"]["B2"]["hyperlink"]["target"] == "https://example.com"
    assert sheet["cells"]["A2"]["fmt"] == "#,##0.000"
    assert sheet["cells"]["A5"]["v"] is None
    assert sheet["cells"]["A5"]["fill"]["fgColor"]["rgb"].endswith("F2F2F2")
    assert sheet["cells"]["C1"]["border"]["left"]["style"] == "thin"
    assert sheet["cells"]["C1"]["border"]["left"]["color"]["rgb"].endswith("D3D3D3")
    assert sheet["cells"]["C1"]["align"]["horizontal"] == "center"
    assert sheet["data_validations"][0]["type"] == "list"
    assert sheet["data_validations"][0]["sqref"] == "D1:D3"

    names = {item["name"]: item for item in signature["defined_names"]}
    assert names["MyName"]["attr_text"] == "'Second'!$A$1"


def _make_layout_workbook(
    path,
    *,
    styled=False,
    value=0,
    formula="=SUM(B2:B3)",
    merged="A1:B1",
    freeze="A3",
    column_width=12.5,
):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"

    sheet["A1"] = "Header"
    sheet["B2"] = value
    sheet["B3"] = 2
    sheet["C2"] = ""
    sheet["D2"] = False
    sheet["E2"] = formula
    sheet["F2"] = "site"
    if merged:
        sheet.merge_cells(merged)
    if freeze:
        sheet.freeze_panes = freeze
    sheet.column_dimensions["B"].width = column_width
    sheet.row_dimensions[3].height = 22.0

    validation = DataValidation(
        type="whole", operator="greaterThan", formula1="0", allow_blank=True
    )
    sheet.add_data_validation(validation)
    validation.add("B2:B3")
    workbook.defined_names["Total"] = DefinedName("Total", attr_text="'Data'!$B$3")

    if styled:
        sheet["A1"].font = Font(name="Segoe UI", size=15, bold=True, color="1F4E79")
        sheet["B2"].fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        sheet["B2"].number_format = "#,##0.000"
        sheet["B3"].border = Border(left=Side(style="thin", color="D3D3D3"))
        sheet["C2"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sheet["D2"].font = Font(italic=True, color="C00000")
        sheet["F2"].hyperlink = "https://example.com"
        sheet.conditional_formatting.add(
            "B2:B3",
            CellIsRule(
                operator="greaterThan",
                formula=["0"],
                stopIfTrue=True,
                fill=PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"),
                font=Font(color="1E7E34", bold=True),
            ),
        )

    workbook.save(path)


def test_layout_signature_ignores_visual_differences(tmp_path):
    plain = tmp_path / "plain.xlsx"
    styled = tmp_path / "styled.xlsx"
    _make_layout_workbook(plain)
    _make_layout_workbook(styled, styled=True)

    plain_layout = xlsx_signature(plain, include_styles=False)
    styled_layout = xlsx_signature(styled, include_styles=False)
    assert plain_layout == styled_layout
    assert "conditional_formatting" not in styled_layout["sheets"]["Data"]
    assert plain_layout["sheets"]["Data"]["cells"]["B2"] == {"v": 0, "is_formula": False}

    styled_full = xlsx_signature(styled)
    assert styled_full != xlsx_signature(plain)
    assert styled_full["sheets"]["Data"]["cells"]["F2"]["hyperlink"]["target"] == "https://example.com"


def test_layout_signature_detects_value_formula_merge_freeze_and_width(tmp_path):
    base = tmp_path / "base.xlsx"
    _make_layout_workbook(base)
    base_layout = xlsx_signature(base, include_styles=False)

    cases = {
        "value": {"value": 1},
        "formula": {"formula": "=ROUND(SUM(B2:B3),2)"},
        "merged": {"merged": "A1:C1"},
        "freeze_panes": {"freeze": "B2"},
        "column_width": {"column_width": 24.0},
    }
    for name, change in cases.items():
        path = tmp_path / f"{name}.xlsx"
        _make_layout_workbook(path, **change)
        assert xlsx_signature(path, include_styles=False) != base_layout, (
            f"layout signature ignored the {name} change"
        )
