"""Shared helpers for the TNS parity harness.

The legacy PySide6 application is the oracle: tests run its core functions and
compare the results with the Rust port. Nothing here modifies legacy/pyqt/.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def run_oracle(fixture_path: Path, output_dir: Path, month: str, year: str):
    """Run legacy process_statement and return (result, progress_events)."""
    from core_engine import process_statement

    events: list[list[object]] = []
    result = process_statement(
        str(fixture_path),
        output_dir=str(output_dir),
        month=month,
        year=year,
        progress_callback=lambda percent, message: events.append([percent, message]),
    )
    return result, events


def normalize_result(result: dict, output_dir: Path) -> dict:
    """Make target paths relative to output_dir so goldens are machine-independent."""
    normalized = dict(result)
    base = str(Path(output_dir).resolve())
    for key in ("target_dir", "target_path"):
        value = normalized.get(key)
        if value:
            path = str(Path(value).resolve())
            normalized[key] = path[len(base):].lstrip("\\/") if path.startswith(base) else path
    return normalized


def diff_dicts(left, right, prefix: str = "") -> list[str]:
    """Return a flat list of differences between two JSON-like values."""
    diffs: list[str] = []
    if (
        isinstance(left, (int, float))
        and isinstance(right, (int, float))
        and not isinstance(left, bool)
        and not isinstance(right, bool)
    ):
        if math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-9):
            return []
        return [f"{prefix}: {left!r} != {right!r}"]
    if type(left) is not type(right):
        return [f"{prefix}: {type(left).__name__} != {type(right).__name__} ({left!r} != {right!r})"]
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left:
                diffs.append(f"{prefix}.{key}: missing on left (right={right[key]!r})")
            elif key not in right:
                diffs.append(f"{prefix}.{key}: missing on right (left={left[key]!r})")
            else:
                diffs += diff_dicts(left[key], right[key], f"{prefix}.{key}")
    elif isinstance(left, list):
        if len(left) != len(right):
            return [f"{prefix}: len {len(left)} != {len(right)}"]
        for index, (a, b) in enumerate(zip(left, right)):
            diffs += diff_dicts(a, b, f"{prefix}[{index}]")
    elif left != right:
        return [f"{prefix}: {left!r} != {right!r}"]
    return diffs


def _color_signature(color):
    if color is None:
        return None
    return {
        "type": getattr(color, "type", None),
        "rgb": getattr(color, "rgb", None),
        "theme": getattr(color, "theme", None),
        "tint": getattr(color, "tint", None),
        "indexed": getattr(color, "indexed", None),
        "auto": getattr(color, "auto", None),
    }


def _font_signature(font):
    if font is None:
        return None
    return {
        "name": font.name,
        "size": font.size,
        "bold": font.bold,
        "italic": font.italic,
        "underline": font.underline,
        "strike": font.strike,
        "vertAlign": font.vertAlign,
        "scheme": font.scheme,
        "family": font.family,
        "charset": font.charset,
        "outline": font.outline,
        "shadow": font.shadow,
        "condense": font.condense,
        "extend": font.extend,
        "color": _color_signature(font.color),
    }


def _fill_signature(fill):
    if fill is None:
        return None
    return {
        "type": getattr(fill, "fill_type", None),
        "fgColor": _color_signature(getattr(fill, "fgColor", None)),
        "bgColor": _color_signature(getattr(fill, "bgColor", None)),
        "gradient": [
            [_color_signature(stop.color), stop.position]
            for stop in getattr(fill, "stop", [])
        ]
        or None,
    }


def _side_signature(side):
    if side is None:
        return None
    return {"style": side.style, "color": _color_signature(side.color)}


def _border_signature(border):
    if border is None:
        return None
    return {
        "left": _side_signature(border.left),
        "right": _side_signature(border.right),
        "top": _side_signature(border.top),
        "bottom": _side_signature(border.bottom),
        "diagonal": _side_signature(border.diagonal),
        "vertical": _side_signature(getattr(border, "vertical", None)),
        "horizontal": _side_signature(getattr(border, "horizontal", None)),
        "diagonalUp": border.diagonalUp,
        "diagonalDown": border.diagonalDown,
        "outline": border.outline,
    }


def _alignment_signature(alignment):
    if alignment is None:
        return None
    return {
        field: getattr(alignment, field, None)
        for field in (
            "horizontal",
            "vertical",
            "wrap_text",
            "text_rotation",
            "shrink_to_fit",
            "indent",
            "relativeIndent",
            "justifyLastLine",
            "readingOrder",
        )
    }


def _protection_signature(protection):
    if protection is None:
        return None
    return {"locked": protection.locked, "hidden": protection.hidden}


def _hyperlink_signature(link):
    if link is None:
        return None
    return {
        "target": link.target,
        "location": link.location,
        "tooltip": link.tooltip,
        "display": link.display,
    }


def _dxf_signature(dxf):
    if dxf is None:
        return None
    number_format = dxf.numFmt
    if number_format is not None and not isinstance(number_format, str):
        number_format = getattr(number_format, "formatCode", str(number_format))
    return {
        "font": _font_signature(dxf.font),
        "fill": _fill_signature(dxf.fill),
        "border": _border_signature(dxf.border),
        "alignment": _alignment_signature(dxf.alignment),
        "protection": _protection_signature(dxf.protection),
        "numFmt": number_format,
    }


def _conditional_rule_signature(rule):
    return {
        "type": rule.type,
        "operator": getattr(rule, "operator", None),
        "formula": [str(value) for value in (rule.formula or [])],
        "priority": rule.priority,
        "stopIfTrue": rule.stopIfTrue,
        "text": getattr(rule, "text", None),
        "timePeriod": getattr(rule, "timePeriod", None),
        "rank": getattr(rule, "rank", None),
        "percent": getattr(rule, "percent", None),
        "bottom": getattr(rule, "bottom", None),
        "aboveAverage": getattr(rule, "aboveAverage", None),
        "equalAverage": getattr(rule, "equalAverage", None),
        "stdDev": getattr(rule, "stdDev", None),
        "dxf": _dxf_signature(rule.dxf),
    }


def _defined_name_signature(defined_name, local_sheet):
    return {
        "name": defined_name.name,
        "local_sheet": local_sheet,
        "attr_text": defined_name.attr_text,
        "hidden": defined_name.hidden,
        "comment": getattr(defined_name, "comment", None),
    }


def _data_validation_signature(validation):
    return {
        "sqref": str(validation.sqref),
        "type": validation.type,
        "operator": validation.operator,
        "formula1": validation.formula1,
        "formula2": validation.formula2,
        "allowBlank": validation.allowBlank,
        "showErrorMessage": validation.showErrorMessage,
        "errorTitle": validation.errorTitle,
        "error": validation.error,
        "promptTitle": validation.promptTitle,
        "prompt": validation.prompt,
    }


def xlsx_signature(path: Path) -> dict:
    """Content signature of an xlsx: sheet order, styles, merges, CF, links.

    Raw xlsx bytes are not deterministic (zip timestamps), so parity compares
    semantic workbook content instead of file hashes. The signature is used by
    both the legacy-oracle tests and the Rust-output tests, so it must stay
    independent from both implementations.
    """
    from openpyxl import load_workbook

    workbook = load_workbook(path)
    try:
        sheets = {}
        for index, ws in enumerate(workbook.worksheets):
            info = {
                "index": index,
                "title": ws.title,
                "state": ws.sheet_state,
                "freeze_panes": str(ws.freeze_panes) if ws.freeze_panes else None,
                "auto_filter": str(ws.auto_filter.ref) if ws.auto_filter.ref else None,
                "print_area": str(ws.print_area) if ws.print_area else None,
                "merged": sorted(str(rng) for rng in ws.merged_cells.ranges),
                "col_widths": {
                    column: {
                        "width": round(dim.width, 6) if dim.width is not None else None,
                        "hidden": bool(dim.hidden),
                        "bestFit": bool(dim.bestFit),
                        "customWidth": bool(dim.customWidth),
                    }
                    for column, dim in ws.column_dimensions.items()
                    if dim.width is not None or dim.hidden or dim.bestFit or dim.customWidth
                },
                "row_heights": {
                    str(row): {
                        "height": round(dim.height, 6) if dim.height is not None else None,
                        "hidden": bool(dim.hidden),
                        "customHeight": bool(dim.customHeight),
                    }
                    for row, dim in ws.row_dimensions.items()
                    if dim.height is not None or dim.hidden or dim.customHeight
                },
                "conditional_formatting": [
                    {
                        "range": str(rng.sqref),
                        "rules": [_conditional_rule_signature(rule) for rule in rng.rules],
                    }
                    for rng in ws.conditional_formatting
                ],
                "data_validations": [
                    _data_validation_signature(validation)
                    for validation in ws.data_validations.dataValidation
                ],
                "cells": {},
            }
            for row in ws.iter_rows():
                for cell in row:
                    if (
                        cell.value is None
                        and cell.hyperlink is None
                        and not getattr(cell, "has_style", False)
                    ):
                        continue
                    protection = _protection_signature(cell.protection)
                    if protection == {"locked": True, "hidden": False}:
                        protection = None
                    info["cells"][cell.coordinate] = {
                        "v": cell.value,
                        "t": cell.data_type,
                        "fmt": cell.number_format,
                        "font": _font_signature(cell.font),
                        "fill": _fill_signature(cell.fill),
                        "align": _alignment_signature(cell.alignment),
                        "border": _border_signature(cell.border),
                        "protection": protection,
                        "hyperlink": _hyperlink_signature(cell.hyperlink),
                    }
            sheets[ws.title] = info

        defined_names = []
        seen = set()
        for ws in workbook.worksheets:
            for defined_name in ws.defined_names.values():
                key = (defined_name.name, ws.title, defined_name.attr_text)
                if key not in seen:
                    seen.add(key)
                    defined_names.append(_defined_name_signature(defined_name, ws.title))
        for defined_name in workbook.defined_names.values():
            key = (defined_name.name, None, defined_name.attr_text)
            if key not in seen:
                seen.add(key)
                defined_names.append(_defined_name_signature(defined_name, None))
        defined_names.sort(key=lambda item: (item["local_sheet"] or "", item["name"]))

        return {
            "sheet_order": [ws.title for ws in workbook.worksheets],
            "defined_names": defined_names,
            "sheets": sheets,
        }
    finally:
        workbook.close()
