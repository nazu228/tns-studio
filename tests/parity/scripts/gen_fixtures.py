#!/usr/bin/env python3
"""Generate deterministic TNS statements for the parity harness.

The layout follows legacy/pyqt/tns_input.py:resolve_layout:
  A type | C point number | D point name | E meter number | I tariff zone |
  J sub type | L read start | M read end | O difference | P coefficient |
  Q main expense | W sub deduction | AB billed volume (col 28).

Outputs: tests/parity/fixtures/*.xlsx and manifest.json.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from openpyxl import Workbook

PARITY_DIR = Path(os.environ.get("TNS_PARITY_DIR") or Path(__file__).resolve().parents[1]).resolve()
FIXTURES_DIR = PARITY_DIR / "fixtures"

HEADER_ROW = 7
DATA_START = 9

COLS = {
    "type": 1,
    "num": 3,
    "name": 4,
    "meter": 5,
    "zone": 9,
    "sub": 10,
    "start": 12,
    "end": 13,
    "diff": 15,
    "coeff": 16,
    "main": 17,
    "sub_deduct": 23,
    "billed": 28,
}

HEADERS = {
    1: "Тип",
    3: "Номер",
    4: "Наименование",
    5: "Заводской номер",
    9: "Зона тарифа",
    10: "Суб. абонент",
    12: "Начальные показания",
    13: "Конечные показания",
    15: "Разность",
    16: "Коэффициент",
    17: "Основной расход",
    23: "Вычитание суб.",
    28: "Начисленный объём",
}


def rnd(value: float) -> float:
    return round(float(value), 6)


def comma_fmt(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def fmt(value, comma_strings: bool):
    if value is None:
        return "—" if comma_strings else None
    if isinstance(value, (int, float)) and comma_strings:
        return comma_fmt(float(value))
    return value


FIXTURES = [
    {
        "file": "dom_april_2026.xlsx",
        "consumer": "ООО «Южный Дом»",
        "contract": "23110603789",
        "period": "Апрель 2026 г.",
        "month": "Апрель",
        "year": "2026",
        "comma_strings": False,
        "houses": [
            {
                "address": "ул. Ленина, д. 1",
                "name": "Дом 1",
                "meters": [
                    {"point": "1.1", "name": "Вводной ПУ 1", "meter": "100101", "zone": "День", "start": 1000.0, "end": 1100.0, "coeff": 1.0, "billed": 100.0},
                    {"point": "1.2", "name": "Вводной ПУ 2", "meter": "100102", "zone": "День", "start": 500.0, "end": 500.0, "coeff": 1.0, "billed": 0.0},
                    {"point": "1.3", "name": "Вводной ПУ 3", "meter": "100103", "zone": "День", "start": 200.0, "end": 240.5, "coeff": 1.0, "billed": 40.5},
                    {"point": "1.4", "name": "Ночной ПУ", "meter": "100104", "zone": "Ночь", "start": 50.0, "end": 62.25, "coeff": 1.0, "billed": 12.25},
                ],
                "subs": [
                    {"point": "1.5", "name": "Субабонент", "meter": "200201", "zone": "ОДН", "start": 0.0, "end": 5.5, "coeff": 1.0, "billed": 5.5},
                ],
            },
            {
                "address": "ул. Мира, д. 3",
                "name": "Дом 2",
                "meters": [
                    {"point": "2.1", "name": "ПУ Т1", "meter": "100201", "zone": "Т1", "start": 300.0, "end": 375.0, "coeff": 1.0, "billed": 75.0},
                    {"point": "2.2", "name": "ПУ ОДН", "meter": "100202", "zone": "ОДН", "start": 10.0, "end": 35.0, "coeff": 1.0, "billed": 25.0},
                ],
                "subs": [],
            },
        ],
    },
    {
        "file": "gorod_april_2026.xlsx",
        "consumer": "ООО «Южный Город»",
        "contract": "23110604327",
        "period": "Апрель 2026 г.",
        "month": "Апрель",
        "year": "2026",
        "comma_strings": False,
        "houses": [
            {
                "address": "ул. Советская, д. 10",
                "name": "Дом 10",
                "meters": [
                    {"point": "1.1", "name": "ПУ День", "meter": "300101", "zone": "День", "start": 1200.0, "end": 1350.0, "coeff": 1.0, "billed": 150.0},
                    {"point": "1.2", "name": "ПУ День 2", "meter": "300102", "zone": "День", "start": 300.0, "end": 330.75, "coeff": 1.0, "billed": 30.75},
                    {"point": "1.3", "name": "ПУ ОДН", "meter": "300103", "zone": "ОДН (ЗР)", "start": 40.0, "end": 55.5, "coeff": 1.0, "billed": 15.5},
                ],
                "subs": [],
            },
            {
                "address": "ул. Гагарина, д. 22",
                "name": "Дом 22",
                "meters": [
                    {"point": "2.1", "name": "ПУ Т1", "meter": "300201", "zone": "Т1", "start": 900.0, "end": 1020.5, "coeff": 1.0, "billed": 120.5},
                    {"point": "2.2", "name": "ПУ Т2", "meter": "300202", "zone": "Т2", "start": 200.0, "end": 222.25, "coeff": 1.0, "billed": 22.25},
                    {"point": "2.3", "name": "ПУ Одноставочный", "meter": "300203", "zone": "Одноставочный", "start": 15.0, "end": 28.75, "coeff": 1.0, "billed": 13.75},
                ],
                "subs": [],
            },
            {
                "address": "ул. Победы, д. 5",
                "name": "Дом 5",
                "meters": [
                    {"point": "3.1", "name": "ПУ Пик", "meter": "300301", "zone": "Пик", "start": 700.0, "end": 811.25, "coeff": 1.0, "billed": 111.25},
                    {"point": "3.2", "name": "ПУ Круглосуточный", "meter": "300302", "zone": "Круглосуточный", "start": 60.0, "end": 84.5, "coeff": 1.0, "billed": 24.5},
                ],
                "subs": [],
            },
        ],
    },
    {
        "file": "dom_march_2026.xlsx",
        "consumer": "ООО «Южный Дом»",
        "contract": "23110603789",
        "period": "Март 2026 г.",
        "month": "Март",
        "year": "2026",
        "comma_strings": True,
        "houses": [
            {
                "address": "ул. Садовая, д. 7",
                "name": "Дом 7",
                "meters": [
                    {"point": "1.1", "name": "ПУ Т1", "meter": "400101", "zone": "Т1", "start": 1000.0, "end": 1200.0, "coeff": 1.0, "billed": 200.0},
                    {"point": "1.2", "name": "ПУ Т2", "meter": "400102", "zone": "Т2", "start": 500.0, "end": 562.5, "coeff": 1.0, "billed": 62.5},
                    {"point": "1.3", "name": "ПУ ОДН", "meter": "400103", "zone": "ОДН", "start": 40.0, "end": 55.25, "coeff": 1.0, "billed": 15.25},
                    {"point": "1.4", "name": "Резервный ПУ", "meter": "400104", "zone": "День", "start": None, "end": None, "coeff": 1.0, "billed": 0.0, "reserve": True},
                ],
                "subs": [
                    {"point": "1.5", "name": "Субабонент", "meter": "400201", "zone": "ОДН", "start": 0.0, "end": 3.5, "coeff": 1.0, "billed": 3.5},
                ],
            },
        ],
    },
]


def build_statement(spec: dict):
    wb = Workbook()
    ws = wb.active
    ws.title = "Ведомость"
    comma = bool(spec.get("comma_strings"))

    ws["D1"] = spec["consumer"]
    ws["D2"] = f"Договор: {spec['contract']}"
    ws["D3"] = spec["period"]
    ws["A5"] = "Тестовая ведомость для parity-тестов"
    for col, text in HEADERS.items():
        ws.cell(HEADER_ROW, col, text)

    row = DATA_START
    house_controls = []
    meter_rows = 0
    sub_rows = 0

    for house in spec["houses"]:
        records = []
        for meter in house["meters"]:
            if meter.get("reserve"):
                start = end = diff = main = None
                billed = 0.0
            else:
                start = meter["start"]
                end = meter["end"]
                diff = None if start is None or end is None else rnd(end - start)
                main = None if diff is None else rnd(diff * meter["coeff"])
                billed = float(main or 0.0)
            records.append({
                "zone": meter["zone"], "point": meter["point"], "name": meter["name"],
                "meter": meter["meter"], "start": start, "end": end, "diff": diff,
                "coeff": meter["coeff"], "main": main, "billed": billed,
            })

        sub_records = []
        for sub in house.get("subs", []):
            diff = rnd(sub["end"] - sub["start"])
            main = rnd(diff * sub["coeff"])
            sub_records.append({
                "zone": sub["zone"], "point": sub["point"], "name": sub["name"],
                "meter": sub["meter"], "start": sub["start"], "end": sub["end"],
                "diff": diff, "coeff": sub["coeff"], "main": main,
            })

        control = rnd(sum(record["billed"] for record in records))
        ws.cell(row, COLS["type"], 100)
        ws.cell(row, COLS["num"], house["address"])
        ws.cell(row, COLS["name"], house["name"])
        ws.cell(row, COLS["billed"], fmt(control, comma))
        house_controls.append(control)
        row += 1

        for record in records:
            ws.cell(row, COLS["type"], 101)
            ws.cell(row, COLS["num"], record["point"])
            ws.cell(row, COLS["name"], record["name"])
            ws.cell(row, COLS["meter"], record["meter"])
            ws.cell(row, COLS["zone"], record["zone"])
            ws.cell(row, COLS["start"], fmt(record["start"], comma))
            ws.cell(row, COLS["end"], fmt(record["end"], comma))
            ws.cell(row, COLS["diff"], fmt(record["diff"], comma))
            ws.cell(row, COLS["coeff"], fmt(record["coeff"], comma))
            ws.cell(row, COLS["main"], fmt(record["main"], comma))
            ws.cell(row, COLS["billed"], fmt(record["billed"], comma))
            meter_rows += 1
            row += 1

        for record in sub_records:
            ws.cell(row, COLS["type"], 102)
            ws.cell(row, COLS["num"], record["point"])
            ws.cell(row, COLS["name"], record["name"])
            ws.cell(row, COLS["meter"], record["meter"])
            ws.cell(row, COLS["zone"], record["zone"])
            ws.cell(row, COLS["start"], fmt(record["start"], comma))
            ws.cell(row, COLS["end"], fmt(record["end"], comma))
            ws.cell(row, COLS["diff"], fmt(record["diff"], comma))
            ws.cell(row, COLS["coeff"], fmt(record["coeff"], comma))
            ws.cell(row, COLS["main"], fmt(record["main"], comma))
            ws.cell(row, COLS["sub_deduct"], fmt(record["main"], comma))
            ws.cell(row, COLS["billed"], fmt(record["main"], comma))
            sub_rows += 1
            row += 1

    statement_total = rnd(sum(house_controls))
    ws.cell(row, COLS["type"], 100)
    ws.cell(row, 2, "Итого:")
    ws.cell(row, COLS["billed"], fmt(statement_total, comma))

    return wb, {
        "houses_count": len(spec["houses"]),
        "statement_total": statement_total,
        "meter_rows": meter_rows,
        "sub_rows": sub_rows,
        "total_row": row,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while chunk := stream.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generator": "scripts/gen_fixtures.py",
        "header_row": HEADER_ROW,
        "data_start": DATA_START,
        "columns": COLS,
        "fixtures": [],
    }
    for spec in FIXTURES:
        wb, stats = build_statement(spec)
        path = FIXTURES_DIR / spec["file"]
        wb.save(path)
        wb.close()
        manifest["fixtures"].append({
            "file": spec["file"],
            "consumer": spec["consumer"],
            "contract": spec["contract"],
            "period": spec["period"],
            "month": spec["month"],
            "year": spec["year"],
            "sha256": sha256_file(path),
            **stats,
        })
        print(f"{spec['file']}: houses={stats['houses_count']} meters={stats['meter_rows']} subs={stats['sub_rows']} total={stats['statement_total']}")
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"fixtures written to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
