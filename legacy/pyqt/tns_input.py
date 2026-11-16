"""Validated layout detection for TNS worksheets; independent of presentation styles."""
import math
import re

def normalize_header(value):
    text=str(value or '').lower().replace('ё','е').replace('_x000d_',' ')
    text=re.sub(r'(?<=\w)-\s*(?=\w)','',text)
    return re.sub(r'[^a-zа-я0-9]+','',text)

def row_type(value):
    try:
        number=float(str(value).strip().replace(',','.'))
        return int(number) if number in (100,101,102) else None
    except (ValueError,TypeError):return None

def resolve_layout(ws):
    max_scan=min(ws.max_row,250);max_col=min(ws.max_column,200)
    candidates=[]
    for col in range(1,max_col+1):
        codes=[row_type(ws.cell(r,col).value) for r in range(1,max_scan+1)]
        headers=[r for r in range(1,min(max_scan,100)+1) if normalize_header(ws.cell(r,col).value)=='тип']
        if 100 in codes and (101 in codes or 102 in codes):
            candidates.append((bool(headers),codes.count(100)+codes.count(101)+codes.count(102),col))
    if candidates:
        candidates.sort(reverse=True)
        if len(candidates)>1 and candidates[0][:2]==candidates[1][:2]:
            raise ValueError('Неоднозначная колонка типов строк. Проверьте заголовок «Тип».')
        type_col=candidates[0][2]
    else:
        # Retain the type header even for an empty table, so the caller can explain it.
        types=[c for c in range(1,max_col+1) for r in range(1,min(max_scan,100)+1) if normalize_header(ws.cell(r,c).value)=='тип']
        type_col=min(types) if types else 1
    first=next((r for r in range(1,ws.max_row+1) if row_type(ws.cell(r,type_col).value)),None)
    if first is None:raise ValueError('Не найдены строки домов и приборов (типы 100/101/102). Выберите исходную ведомость ТНС.')
    shift=type_col-1
    cols={k:v+shift for k,v in {'col_type':1,'col_point_num':3,'col_point_name':4,'col_meter_num':5,'col_zone':9,'col_sub_type':10,'col_read_start':12,'col_read_end':13,'col_diff':15,'col_coeff':16,'col_main_exp':17,'col_sub_deduct':23,'col_billed_vol':28}.items()}
    found=set()
    for r in range(1,first):
        for c in range(1,max_col+1):
            val=normalize_header(ws.cell(r,c).value)
            key=None
            if 'начис' in val and 'объем' in val:key='col_billed_vol'
            elif 'зона' in val and 'тариф' in val:key='col_zone'
            elif 'завод' in val and 'номер' in val:key='col_meter_num'
            elif 'вычитан' in val and 'суб' in val:key='col_sub_deduct'
            elif 'суб' in val and 'абонент' in val:key='col_sub_type'
            elif 'разност' in val:key='col_diff'
            elif 'коэф' in val:key='col_coeff'
            elif 'основн' in val and 'расход' in val:key='col_main_exp'
            elif val in ('нач','начальныепоказания'):key='col_read_start'
            elif val in ('кон','конечныепоказания'):key='col_read_end'
            elif val=='наименование':key='col_point_name'
            elif val=='номер':key='col_point_num'
            if key:
                cols[key]=c;found.add(key)
    # Only headerless legacy fixtures with the exact known width get a fallback.
    if 'col_billed_vol' not in found and not (not found and type_col==1 and ws.max_column in (28,29)):
        raise ValueError('Не найдена колонка «Начисленный объем». Нельзя безопасно выбрать расход по номеру столбца.')
    if 'col_zone' not in found and found:
        raise ValueError('Не найдена колонка «Зона тарифа». Проверьте исходную ведомость.')
    cols['first_data_row']=first
    cols['col_house_name']=cols['col_point_num']
    cols['col_total_label']=max(type_col+1,cols['col_point_num']-1)
    return cols

def total_row(ws,row,cols):
    return any(normalize_header(ws.cell(row,c).value).startswith(('итого','всего')) for c in range(cols['col_type']+1,cols['col_point_name']+1))

def numeric_value(value,coordinate):
    if value is None or str(value).strip() in ('','-','—'):return 0.0
    try:number=float(str(value).strip().replace('\xa0','').replace(' ','').replace(',','.'))
    except (TypeError,ValueError):raise ValueError(f'В ячейке {coordinate} некорректный расход: {value!r}.')
    if not math.isfinite(number):raise ValueError(f'В ячейке {coordinate} расход не является конечным числом.')
    return number

def extract_metadata(ws):
    strings=[str(cell.value).strip() for row in ws.iter_rows(min_row=1,max_row=min(ws.max_row,30),max_col=min(ws.max_column,100)) for cell in row if cell.value is not None]
    contract=next((v for v in strings if '23110604327' in v or '23110603789' in v),'')
    consumer=next((v for v in strings if any(k in normalize_header(v) for k in ('южныйгород','южныйдом'))),'')
    pattern=r'(?:январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья])\s+20\d{2}'
    period=next((m.group(0) for v in strings for m in [re.search(pattern,v,re.I)] if m),'')
    return consumer,contract,period
