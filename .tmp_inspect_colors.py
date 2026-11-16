from openpyxl import load_workbook

wb = load_workbook('tests/parity/fixtures/golden/dom_april_2026.xlsx')
ws = wb['Сводка по домам']
for coord in ['A1', 'A3', 'A5', 'A6', 'B6', 'C6', 'F6', 'H6', 'I6', 'J6', 'A8', 'B8']:
    c = ws[coord]
    print(coord, 'value', repr(c.value), 'font', c.font.name, c.font.sz, c.font.bold, c.font.italic, c.font.color.rgb if c.font.color else None, 'fill', c.fill.fill_type, c.fill.fgColor.rgb if c.fill.fill_type == 'solid' else None, 'border', c.border.left.style, c.border.left.color.rgb if c.border.left.color else None, c.border.bottom.style, c.border.bottom.color.rgb if c.border.bottom.color else None)
ws2 = wb['Ведомость ЭП']
for coord in ['A5', 'A9', 'AD9', 'AE9', 'AF9', 'AL9', 'AD10', 'AD18']:
    c = ws2[coord]
    print('EP', coord, 'value', repr(c.value), 'font', c.font.name, c.font.sz, c.font.bold, c.font.color.rgb if c.font.color else None, 'fill', c.fill.fill_type, c.fill.fgColor.rgb if c.fill.fill_type == 'solid' else None, 'border', c.border.left.style, c.border.left.color.rgb if c.border.left.color else None, c.border.bottom.style, c.border.bottom.color.rgb if c.border.bottom.color else None, 'fmt', c.number_format, 'align', c.alignment.horizontal, c.alignment.vertical, c.alignment.wrap_text)
