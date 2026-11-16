"""Shared helpers for the TNS parity harness.

The legacy PySide6 application is the oracle: tests run its core functions and
compare the results with the Rust port. Nothing here modifies legacy/pyqt/.
"""
from __future__ import annotations

import hashlib
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


def xlsx_signature(path: Path) -> dict:
    """Content signature of an xlsx: values, formulas, styles, merges, widths.

    Raw xlsx bytes are not deterministic (zip timestamps), so parity compares
    the workbook content instead of file hashes.
    """
    from openpyxl import load_workbook

    def color_rgb(color):
        if color is None:
            return None
        try:
            return color.rgb
        except Exception:
            return f"{color.type}:{color.theme}:{color.indexed}"

    workbook = load_workbook(path)
    try:
        sheets = {}
        for ws in workbook.worksheets:
            info = {
                "title": ws.title,
                "freeze_panes": str(ws.freeze_panes),
                "merged": sorted(str(rng) for rng in ws.merged_cells.ranges),
                "col_widths": {
                    col: round(dim.width, 6)
                    for col, dim in ws.column_dimensions.items()
                    if dim.width is not None
                },
                "row_heights": {
                    r: round(dim.height, 6)
                    for r, dim in ws.row_dimensions.items()
                    if dim.height is not None
                },
                "conditional_formatting": [
                    [str(rng.sqref), [[rule.operator, [str(f) for f in rule.formula]] for rule in rng.rules]]
                    for rng in ws.conditional_formatting
                ],
                "cells": {},
            }
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is None:
                        continue
                    font = cell.font
                    fill = cell.fill
                    alignment = cell.alignment
                    info["cells"][cell.coordinate] = {
                        "v": cell.value,
                        "t": cell.data_type,
                        "fmt": cell.number_format,
                        "font": [font.name, font.bold, font.italic, font.size, color_rgb(font.color)],
                        "fill": [fill.fill_type, color_rgb(fill.fgColor) if fill.fill_type == "solid" else None],
                        "align": [alignment.horizontal, alignment.vertical, alignment.wrap_text],
                        "border": {
                            side: [getattr(cell.border, side).style, color_rgb(getattr(cell.border, side).color)]
                            for side in ("left", "right", "top", "bottom")
                        },
                        "hyperlink": cell.hyperlink.target if cell.hyperlink else None,
                    }
            sheets[ws.title] = info
        return sheets
    finally:
        workbook.close()
