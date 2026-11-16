from openpyxl import load_workbook

p = 'tests/parity/fixtures/golden/dom_april_2026.xlsx'
wb = load_workbook(p)
for ws in wb.worksheets:
    print('SHEET', ws.title, 'freeze', ws.freeze_panes, 'merges', [str(r) for r in ws.merged_cells.ranges])
    print('widths', {k: v.width for k, v in ws.column_dimensions.items() if v.width})
    print('heights', {k: v.height for k, v in ws.row_dimensions.items() if v.height})
    print('cf', [(str(rng.sqref), [(rule.operator, rule.formula) for rule in rng.rules]) for rng in ws.conditional_formatting])
    empties = []
    for row in ws.iter_rows():
        for c in row:
            if c.value == '':
                empties.append((c.coordinate, repr(c.value), c.font.name, c.font.sz, c.fill.fill_type, c.number_format))
    print('empty-string cells', empties[:20], 'count', len(empties))
    links = [(c.coordinate, c.hyperlink.target if c.hyperlink else None) for row in ws.iter_rows() for c in row if c.hyperlink]
    print('links', links[:5])
    for coord in ['A1', 'A2', 'A3', 'A5', 'A6', 'B6', 'C6', 'H6', 'A' + str(ws.max_row), 'B' + str(ws.max_row)]:
        c = ws[coord]
        print(coord, repr(c.value), c.data_type, c.number_format, c.font.name, c.font.sz, c.font.bold, c.fill.fill_type, c.fill.fgColor.rgb if c.fill.fill_type == 'solid' else None, c.alignment.horizontal, c.alignment.vertical, c.border.left.style, c.border.bottom.style)
    print('max', ws.max_row, ws.max_column)
