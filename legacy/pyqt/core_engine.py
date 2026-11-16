import os
import sys
import datetime
from tns_input import resolve_layout, row_type, total_row, numeric_value, extract_metadata
import tempfile
import hashlib
from functools import lru_cache
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


def safe_float(val, default=0.0):
    """
    Безопасное преобразование ячеек в float с поддержкой пробелов,
    неразрывных пробелов, запятых, дефисов и пустых значений.
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
    if s in ('', '-', '—', 'none', 'null', 'nan'):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def classify_zone(zone_str):
    """
    Умный и устойчивый классификатор зон тарифов ТНС:
    - 'day': День, Дневная, Пик, Полупик, Т1, T1, Т-1
    - 'night': Ночь, Ночная, Т2, T2, Т-2
    - 'odn': ОДН, Одноставочный, Однозонный, Круглосуточный, ЗР, без дифференциации
    """
    if not zone_str:
        return 'odn'
    
    z = str(zone_str).lower().strip().replace('\xa0', ' ')
    z = z.replace('t', 'т').replace('c', 'с')
    if any(word in z for word in ('одн','одностав','однозон','круглосуточ','без дифференциации')):
        return 'odn'
    
    # Ночные тарифы (Т2)
    if any(w in z for w in ['ночь', 'ноч', 'т2', 'т-2']):
        return 'night'
        
    # Дневные / пиковые / полупиковые тарифы (Т1)
    if any(w in z for w in ['день', 'дн', 'пик', 'полупик', 'т1', 'т-1']):
        return 'day'
        
    # Все остальные тарифы (ОДН, ЗР, МАКСМОЩ, Одноставочные, Круглосуточные)
    return 'odn'


def resolve_columns(ws):
    return resolve_layout(ws)


def safe_save_workbook(wb, target_path):
    """
    Безопасное сохранение книги Excel.
    Если файл открыт пользователем в Microsoft Excel, перехватывает PermissionError
    и сохраняет результат в копию, предотвращая сбой программы.
    """
    folder=os.path.dirname(os.path.abspath(target_path))
    os.makedirs(folder,exist_ok=True)
    fd,temp_path=tempfile.mkstemp(prefix=".tns-",suffix=".xlsx",dir=folder)
    os.close(fd)
    try:
        wb.save(temp_path)
        try:
            os.replace(temp_path,target_path)
            return target_path,None
        except PermissionError:
            base,ext=os.path.splitext(target_path)
            alt_path=f"{base}_(копия_{datetime.datetime.now():%Y%m%d_%H%M%S_%f}){ext}"
            os.replace(temp_path,alt_path)
            return alt_path,"Основной файл открыт в Excel; результат сохранен в отдельную копию."
    finally:
        if os.path.exists(temp_path):os.remove(temp_path)


def detect_statement_type(filepath):
    try:
        path=os.path.abspath(filepath)
        with open(path,"rb") as stream:fingerprint=hashlib.file_digest(stream,"sha256").hexdigest()
        return _detect_statement_type_cached(path,fingerprint)
    except Exception as error:return None,str(error),""

@lru_cache(maxsize=32)
def _detect_statement_type_cached(filepath,fingerprint):
    """
    Определяет тип ведомости: 'dom' (Южный Дом), 'gorod' (Южный Город) или None
    """
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        try:resolve_columns(ws)
        except ValueError as error:
            wb.close()
            return None,str(error),""
        consumer, contract, _ = extract_metadata(ws)
        consumer=consumer.lower()
        wb.close()
        
        if "город" in consumer or "23110604327" in contract:
            return "gorod", "ООО \"Южный город\"", "23110604327"
        elif "дом" in consumer or "23110603789" in contract:
            return "dom", "ООО \"Южный Дом\"", "23110603789"
        else:
            return "unknown", consumer or "Неизвестно", contract
    except Exception as e:
        return None, str(e), ""


def process_statement(source_path, output_dir=None, custom_filename=None, month=None, year=None, progress_callback=None, cancel_callback=None):
    """
    Обрабатывает ведомость электропотребления ТНС Энерго и создает итоговый Excel файл.
    Двухстраничная модель:
    - Лист 1: 'Сводка по домам' (Дашборд с простыми ссылками ='Ведомость ЭП'!XY)
    - Лист 2: 'Ведомость ЭП' (Полная исходная ведомость 1С со сквозными формулами сложения по ст. AB)
    """
    if progress_callback:
        progress_callback(5, f"Чтение файла: {os.path.basename(source_path)}...")

    def check_cancelled():
        if cancel_callback and cancel_callback():raise InterruptedError("Расчет отменен пользователем.")
    check_cancelled()
    wb = openpyxl.load_workbook(source_path)
    value_wb=None
    try:
        ws_source = wb.active
        cols = resolve_columns(ws_source)
        original_sheet_title=ws_source.title
        value_wb = None
        value_ws = None
        def billed_value(row):
            cell=ws_source.cell(row,cols['col_billed_vol'])
            if cell.data_type=='f':
                nonlocal value_wb,value_ws
                if value_wb is None:
                    value_wb=openpyxl.load_workbook(source_path,read_only=True,data_only=True)
                    value_ws=value_wb[original_sheet_title]
                cached=value_ws.cell(row,cols['col_billed_vol']).value
                if cached is None:raise ValueError(f"Формула в {cell.coordinate} не пересчитана. Откройте исходный файл в Excel, пересчитайте и сохраните его.")
                return numeric_value(cached,cell.coordinate)
            return numeric_value(cell.value,cell.coordinate)
        source_sheet_name = "Ведомость ЭП"
        ws_source.title = source_sheet_name
        ws_source.views.sheetView[0].showGridLines = True

        # Метаданные из шапки
        consumer_orig,contract_orig,period_orig=extract_metadata(ws_source)

        # Определяем организацию
        st_type, consumer_name, contract_num = detect_statement_type(source_path)
        if not consumer_name or st_type == "unknown":
            consumer_name = consumer_orig or "ООО \"Южный Дом\""
            contract_num = contract_orig
    
        # Определяем период
        if month and year:
            period_str = f"{month} {year} г."
            period_slug = f"{month}_{year}"
            subfolder_name = f"{month} {year} ТНС"
        elif period_orig:
            period_str = period_orig
            period_slug = period_orig.replace(" ", "_").replace("г.", "").strip("_")
            clean_period = period_orig.replace("г.", "").strip()
            subfolder_name = f"{clean_period} ТНС"
        else:
            period_str = "Август 2026 г."
            period_slug = "Август_2026"
            subfolder_name = "Август 2026 ТНС"

        # Базовая папка
        if not output_dir:
            output_dir = os.path.dirname(os.path.abspath(source_path))

        # Создание подпапки "<Месяц> <Год> ТНС"
        if os.path.basename(os.path.normpath(output_dir)).lower() == subfolder_name.lower():
            target_dir = output_dir
        else:
            target_dir = os.path.join(output_dir, subfolder_name)
        os.makedirs(target_dir, exist_ok=True)

        # Имя выходного файла
        if custom_filename:
            out_name = custom_filename
            if not out_name.endswith(".xlsx"):
                out_name += ".xlsx"
        else:
            prefix = "Город" if st_type == "gorod" else "Дом"
            out_name = f"{prefix}_{period_slug}.xlsx"

        target_path = os.path.join(target_dir, out_name)

        if progress_callback:
            progress_callback(15, "Анализ структуры столбцов и приборов учета...")

        # Умное определение номеров колонок (динамически)
        col_t = cols['col_type']
        col_z = cols['col_zone']
        col_name = cols['col_point_name']
        col_meter = cols['col_meter_num']
        col_diff = cols['col_diff']
        col_billed = cols['col_billed_vol']
        col_billed_letter = get_column_letter(col_billed)

        # Поиск домов и приборов
        houses = []
        current_house = None
        statement_total_row = None

        for r in range(cols['first_data_row'], ws_source.max_row + 1):
            check_cancelled()
            c1 = row_type(ws_source.cell(r, col_t).value)
            c2 = str(ws_source.cell(r, cols['col_total_label']).value or "").strip()
            c3 = str(ws_source.cell(r, cols['col_house_name']).value or "").strip()

            # Тип 100: заголовок дома или общий итог
            if c1 == 100 or str(c1) == '100':
                if total_row(ws_source,r,cols):
                    statement_total_row = r
                    break
                else:
                    current_house = {
                        'name': c3,
                        'header_row': r,
                        'day_rows': [],
                        'night_rows': [],
                        'odn_rows': [],
                        'sub_rows': []
                    }
                    houses.append(current_house)
            # Тип 101: вводной прибор учета начисления дома
            elif (c1 == 101 or str(c1) == '101') and current_house:
                zone_raw = ws_source.cell(r, col_z).value
                zone_type = classify_zone(zone_raw)
                if zone_type == 'day':
                    current_house['day_rows'].append(r)
                elif zone_type == 'night':
                    current_house['night_rows'].append(r)
                else:
                    current_house['odn_rows'].append(r)
            # Тип 102: субабонент (вычитается поставщиком)
            elif (c1 == 102 or str(c1) == '102') and current_house:
                current_house['sub_rows'].append(r)

        if not houses:
            wb.close()
            raise ValueError("Не найдены дома в исходной ведомости. Проверьте типы строк и структуру таблицы.")
        if statement_total_row is None:
            wb.close()
            raise ValueError("Не найдена итоговая строка ведомости «Итого». Расчет остановлен, чтобы не создать циклические формулы.")
        for house in houses:
            for row in [house['header_row'],*house['day_rows'],*house['night_rows'],*house['odn_rows']]:
                billed_value(row)
        billed_value(statement_total_row)

        if progress_callback:
            progress_callback(35, f"Найдено домов: {len(houses)}. Разметка и добавление формул в Ведомость ЭП...")

        # =========================================================================
        # РАСЧЕТНЫЕ СТОЛБЦЫ НА ЛИСТЕ "ВЕДОМОСТЬ ЭП"
        # =========================================================================
        font_family = "Segoe UI"
        num_fmt_vol = "#,##0.000"

        border_thin = Side(style="thin", color="D3D3D3")
        border_double = Side(style="double", color="1F4E79")

        box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
        total_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_double)

        fill_day_cat = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        fill_night_cat = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        fill_odn_cat = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        fill_sub_cat = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        fill_house_hdr = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
        fill_calc_row = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
        fill_total_row = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

        green_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        green_font = Font(name=font_family, size=9, bold=True, color="1E7E34")
        red_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
        red_font = Font(name=font_family, size=9, bold=True, color="B71C1C")

        # Начальный столбец для расчетных блоков на листе Ведомость ЭП
        col_start = max(ws_source.max_column + 2, 30)
        col_cat = col_start
        col_stat = col_start + 1
        col_day = col_start + 2
        col_night = col_start + 3
        col_odn = col_start + 4
        col_tot = col_start + 5
        col_ctrl = col_start + 6
        col_diff = col_start + 7
        col_audit = col_start + 8

        col_day_letter = get_column_letter(col_day)
        col_night_letter = get_column_letter(col_night)
        col_odn_letter = get_column_letter(col_odn)
        col_tot_letter = get_column_letter(col_tot)
        col_ctrl_letter = get_column_letter(col_ctrl)
        col_diff_letter = get_column_letter(col_diff)

        headers_ep = {
            col_cat: "Категория для начисления",
            col_stat: "Статус прибора учета",
            col_day: "⚡ Энергия День (кВт*ч)",
            col_night: "🌙 Энергия Ночь (кВт*ч)",
            col_odn: "💡 ОДН (кВт*ч)",
            col_tot: "ИТОГО по формулам (кВт*ч)",
            col_ctrl: "Контроль ТНС (кВт*ч)",
            col_diff: "Отклонение (кВт*ч)",
            col_audit: "Аудит баланса"
        }

        hdr_font_ep = Font(name=font_family, size=9, bold=True, color="FFFFFF")
        hdr_fill_ep = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")

        for c_idx, h_text in headers_ep.items():
            cell = ws_source.cell(10, c_idx, h_text)
            cell.font = hdr_font_ep
            cell.fill = hdr_fill_ep
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        font_pu = Font(name=font_family, size=9)
        font_bold_pu = Font(name=font_family, size=9, bold=True)
        font_calc_hdr = Font(name=font_family, size=10, bold=True)

        preview_data = []

        for idx, h in enumerate(houses, 1):
            check_cancelled()
            hr = h['header_row']
        
            # 1. Разметка счетчиков Дня
            for r in h['day_rows']:
                ws_source.cell(r, col_cat, "⚡ День").fill = fill_day_cat
                ws_source.cell(r, col_cat).font = font_bold_pu
                v = billed_value(r)
                st = "В работе (с расходом)" if v > 0 else "⚪ Резерв (0 кВт*ч, АВР-2)"
                c_st = ws_source.cell(r, col_stat, st)
                c_st.font = font_bold_pu if v > 0 else font_pu

            # 2. Разметка счетчиков Ночи
            for r in h['night_rows']:
                ws_source.cell(r, col_cat, "🌙 Ночь").fill = fill_night_cat
                ws_source.cell(r, col_cat).font = font_bold_pu
                v = billed_value(r)
                st = "В работе (с расходом)" if v > 0 else "⚪ Резерв (0 кВт*ч, АВР-2)"
                c_st = ws_source.cell(r, col_stat, st)
                c_st.font = font_bold_pu if v > 0 else font_pu

            # 3. Разметка счетчиков ОДН
            for r in h['odn_rows']:
                ws_source.cell(r, col_cat, "💡 ОДН").fill = fill_odn_cat
                ws_source.cell(r, col_cat).font = font_bold_pu
                v = billed_value(r)
                st = "В работе (с расходом)" if v > 0 else "⚪ Резерв (0 кВт*ч, АВР-2)"
                c_st = ws_source.cell(r, col_stat, st)
                c_st.font = font_bold_pu if v > 0 else font_pu

            # 4. Разметка субабонентов
            for r in h['sub_rows']:
                ws_source.cell(r, col_cat, "🛡️ Субабонент").fill = fill_sub_cat
                ws_source.cell(r, col_cat).font = font_pu
                ws_source.cell(r, col_stat, "Вычтен ТНС (не включен)").font = font_pu

            # 5. Формулы в строке заголовка дома (Тип 100, строка hr)
            ws_source.cell(hr, col_cat, "ДОМ / ОБЪЕКТ").fill = fill_house_hdr
            ws_source.cell(hr, col_cat).font = font_bold_pu
            total_pu_house = len(h['day_rows']) + len(h['night_rows']) + len(h['odn_rows'])
            ws_source.cell(hr, col_stat, f"{total_pu_house} ПУ").font = font_bold_pu

            # Формула День
            if h['day_rows']:
                d_cells = ', '.join([f'{col_billed_letter}{r}' for r in h['day_rows']])
                ws_source.cell(hr, col_day, f'=SUM({d_cells})')
            else:
                ws_source.cell(hr, col_day, 0.0)

            # Формула Ночь
            if h['night_rows']:
                n_cells = ', '.join([f'{col_billed_letter}{r}' for r in h['night_rows']])
                ws_source.cell(hr, col_night, f'=SUM({n_cells})')
            else:
                ws_source.cell(hr, col_night, 0.0)

            # Формула ОДН
            if h['odn_rows']:
                o_cells = ', '.join([f'{col_billed_letter}{r}' for r in h['odn_rows']])
                ws_source.cell(hr, col_odn, f'=SUM({o_cells})')
            else:
                ws_source.cell(hr, col_odn, 0.0)

            # Формулы ИТОГО, Контроль ТНС, Отклонение, Аудит
            ws_source.cell(hr, col_tot, f'={col_day_letter}{hr}+{col_night_letter}{hr}+{col_odn_letter}{hr}')
            ws_source.cell(hr, col_ctrl, f'={col_billed_letter}{hr}')
            ws_source.cell(hr, col_diff, f'=ROUND({col_tot_letter}{hr}-{col_ctrl_letter}{hr}, 3)')
            ws_source.cell(hr, col_audit, f'=IF({col_diff_letter}{hr}=0, "✔ Сошлось", "❌ Ошибка")')

            for c in range(col_day, col_diff + 1):
                cell = ws_source.cell(hr, c)
                cell.number_format = num_fmt_vol
                cell.font = font_calc_hdr
                cell.fill = fill_calc_row
                cell.border = box_border

            cell_aud = ws_source.cell(hr, col_audit)
            cell_aud.font = green_font
            cell_aud.fill = green_fill
            cell_aud.border = box_border

            # Подсчет показателей дома для UI превью
            actual_day = sum(billed_value(r) for r in h['day_rows'])
            actual_night = sum(billed_value(r) for r in h['night_rows'])
            actual_odn = sum(billed_value(r) for r in h['odn_rows'])
            actual_total = actual_day + actual_night + actual_odn
            ctrl_val = billed_value(hr)
            delta_house = round(actual_total - ctrl_val, 3)

            all_meters = h['day_rows'] + h['night_rows'] + h['odn_rows']
            res_cnt = sum(1 for r in all_meters if billed_value(r) == 0)
            act_cnt = len(all_meters) - res_cnt

            preview_data.append({
                "num": idx,
                "name": h['name'],
                "day": actual_day,
                "night": actual_night,
                "odn": actual_odn,
                "simple": actual_odn,
                "total": actual_total,
                "control": ctrl_val,
                "diff": delta_house,
                "meters": f"{act_cnt} раб. / {res_cnt} рез.",
                "meters_active": act_cnt, "meters_res": res_cnt
            })

        # Итоговая строка ведомости на листе Ведомость ЭП
        if statement_total_row:
            h_first = houses[0]['header_row']
            h_last = houses[-1]['header_row']
            ws_source.cell(statement_total_row, col_cat, "ИТОГО ПО ВЕДОМОСТИ").font = font_calc_hdr
            ws_source.cell(statement_total_row, col_cat).fill = fill_total_row
            ws_source.cell(statement_total_row, col_day, f'=SUM({col_day_letter}{h_first}:{col_day_letter}{h_last})')
            ws_source.cell(statement_total_row, col_night, f'=SUM({col_night_letter}{h_first}:{col_night_letter}{h_last})')
            ws_source.cell(statement_total_row, col_odn, f'=SUM({col_odn_letter}{h_first}:{col_odn_letter}{h_last})')
            ws_source.cell(statement_total_row, col_tot, f'=SUM({col_tot_letter}{h_first}:{col_tot_letter}{h_last})')
            ws_source.cell(statement_total_row, col_ctrl, f'={col_billed_letter}{statement_total_row}')
            ws_source.cell(statement_total_row, col_diff, f'=ROUND({col_tot_letter}{statement_total_row}-{col_ctrl_letter}{statement_total_row}, 3)')
            ws_source.cell(statement_total_row, col_audit, f'=IF({col_diff_letter}{statement_total_row}=0, "✔ 100% БАЛАНС", "❌ ОШИБКА")')

            for c in range(col_day, col_diff + 1):
                cell = ws_source.cell(statement_total_row, c)
                cell.number_format = num_fmt_vol
                cell.font = font_calc_hdr
                cell.fill = fill_total_row
                cell.border = total_border

            c_aud_tot = ws_source.cell(statement_total_row, col_audit)
            c_aud_tot.font = green_font
            c_aud_tot.fill = green_fill
            c_aud_tot.border = total_border

        # Настройка ширины расчетных столбцов на листе Ведомость ЭП
        ep_widths = {
            col_cat: 24, col_stat: 28, col_day: 18, col_night: 18,
            col_odn: 18, col_tot: 22, col_ctrl: 22, col_diff: 16, col_audit: 18
        }
        for c_idx, w in ep_widths.items():
            ws_source.column_dimensions[get_column_letter(c_idx)].width = w

        if progress_callback:
            progress_callback(65, "Построение листа «Сводка по домам» (Дашборд)...")

        # =========================================================================
        # ЛИСТ 1: "Сводка по домам" (Дашборд с простыми ссылками)
        # =========================================================================
        ws_summary = wb.create_sheet("Сводка по домам", 0)
        ws_summary.views.sheetView[0].showGridLines = True
        ws_summary.freeze_panes = "C6"

        # Шапка дашборда
        ws_summary.merge_cells("A1:J1")
        ws_summary["A1"] = f"СВОДНАЯ ВЕДОМОСТЬ НАЧИСЛЕНИЙ ЭЛЕКТРОЭНЕРГИИ — {consumer_name.upper()}"
        ws_summary["A1"].font = Font(name=font_family, size=13, bold=True, color="1F4E79")
        ws_summary["A1"].alignment = Alignment(horizontal="left", vertical="center")
        ws_summary.row_dimensions[1].height = 24

        ws_summary.merge_cells("A2:J2")
        ws_summary["A2"] = f"Месяц: {period_str} | Договор: {contract_num} | Источник: Ведомость ТНС Энерго | Контроль: столбец AB"
        ws_summary["A2"].font = Font(name=font_family, size=9, italic=True, color="555555")
        ws_summary["A2"].alignment = Alignment(horizontal="left", vertical="center")
        ws_summary.row_dimensions[2].height = 18

        ws_summary.merge_cells("A3:J3")
        ws_summary["A3"] = "✔ Все формулы расчета размещены на листе «Ведомость ЭП». Ячейки сводки ссылаются прямо на расчетные формулы."
        ws_summary["A3"].font = Font(name=font_family, size=9, bold=True, color="1E7E34")
        ws_summary["A3"].fill = green_fill
        ws_summary["A3"].alignment = Alignment(horizontal="left", vertical="center")
        ws_summary.row_dimensions[3].height = 20

        # Заголовки таблицы сводки
        dash_headers = [
            "№", "Адрес дома (Объект)", "⚡ Энергия День (кВт*ч)", "🌙 Энергия Ночь (кВт*ч)",
            "💡 ОДН (кВт*ч)", "ИТОГО начислено (кВт*ч)", "Контроль ведомость (ст. AB)",
            "Отклонение (кВт*ч)", "Строки ведомости", "Кол-во ПУ"
        ]

        hdr_r = 5
        ws_summary.row_dimensions[hdr_r].height = 28
        for idx, text in enumerate(dash_headers, 1):
            cell = ws_summary.cell(hdr_r, idx, text)
            cell.font = Font(name=font_family, size=9, bold=True, color="FFFFFF")
            cell.fill = hdr_fill_ep
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = box_border

        # Заполнение строк домов на дашборде
        dr = 6
        for idx, h in enumerate(houses, 1):
            check_cancelled()
            hr = h['header_row']
            all_meters = h['day_rows'] + h['night_rows'] + h['odn_rows']
            min_r = min(all_meters) if all_meters else hr
            max_r = max(all_meters) if all_meters else hr
            res_cnt = sum(1 for r in all_meters if billed_value(r) == 0)
            act_cnt = len(all_meters) - res_cnt

            ws_summary.row_dimensions[dr].height = 22

            # 1. Номер
            ws_summary.cell(dr, 1, idx).alignment = Alignment(horizontal="center", vertical="center")

            # 2. Название дома (ссылка на ячейку ведомости ЭП)
            adr_cell = ws_summary.cell(dr, 2, f"='{source_sheet_name}'!{get_column_letter(cols['col_house_name'])}{hr}")
            adr_cell.font = Font(name=font_family, size=10, bold=True, color="0D6EFD")
            adr_cell.alignment = Alignment(horizontal="left", vertical="center")
            adr_cell.hyperlink = f"#'{source_sheet_name}'!{col_day_letter}{hr}"

            # 3. Энергия День: простая ссылка на формулу в Ведомости ЭП
            c_day = ws_summary.cell(dr, 3, f"='{source_sheet_name}'!{col_day_letter}{hr}")
            c_day.fill = fill_day_cat

            # 4. Энергия Ночь: простая ссылка на формулу в Ведомости ЭП
            c_night = ws_summary.cell(dr, 4, f"='{source_sheet_name}'!{col_night_letter}{hr}")
            c_night.fill = fill_night_cat

            # 5. ОДН: простая ссылка на формулу в Ведомости ЭП
            c_odn = ws_summary.cell(dr, 5, f"='{source_sheet_name}'!{col_odn_letter}{hr}")
            c_odn.fill = fill_odn_cat

            # 6. ИТОГО: сумма трех показателей
            c_tot = ws_summary.cell(dr, 6, f"=C{dr}+D{dr}+E{dr}")
            c_tot.font = Font(name=font_family, size=10, bold=True)

            # 7. Контроль ведомость: ссылка на строку 100 столбец AB
            c_ctrl = ws_summary.cell(dr, 7, f"='{source_sheet_name}'!{col_billed_letter}{hr}")

            # 8. Отклонение: ИТОГО - Контроль
            c_diff = ws_summary.cell(dr, 8, f"=ROUND(F{dr}-G{dr}, 3)")
            c_diff.font = Font(name=font_family, size=10, bold=True)

            for c in [c_day, c_night, c_odn, c_tot, c_ctrl, c_diff]:
                c.number_format = num_fmt_vol
                c.alignment = Alignment(horizontal="right", vertical="center")
                if c.font is None:
                    c.font = Font(name=font_family, size=10)

            # 9. Строки ведомости
            ws_summary.cell(dr, 9, f"стр. {min_r} – {max_r}").alignment = Alignment(horizontal="center", vertical="center")
            ws_summary.cell(dr, 9).font = Font(name=font_family, size=9, color="555555")

            # 10. Количество приборов
            ws_summary.cell(dr, 10, f"{len(all_meters)} ПУ ({act_cnt} раб. / {res_cnt} рез.)").alignment = Alignment(horizontal="center", vertical="center")
            ws_summary.cell(dr, 10).font = Font(name=font_family, size=9, color="333333")

            for c_col in range(1, 11):
                ws_summary.cell(dr, c_col).border = box_border

            dr += 1

        # Строка ИТОГО ПО ВСЕМ ДОМАМ
        tot_dr = dr
        ws_summary.row_dimensions[tot_dr].height = 24
        ws_summary.cell(tot_dr, 1, "")
        ws_summary.cell(tot_dr, 2, "ИТОГО ПО ВСЕМ ДОМАМ:").font = font_calc_hdr
        ws_summary.cell(tot_dr, 2).alignment = Alignment(horizontal="right", vertical="center")

        start_r = 6
        last_r = tot_dr - 1

        ws_summary.cell(tot_dr, 3, f"=SUM(C{start_r}:C{last_r})")
        ws_summary.cell(tot_dr, 4, f"=SUM(D{start_r}:D{last_r})")
        ws_summary.cell(tot_dr, 5, f"=SUM(E{start_r}:E{last_r})")
        ws_summary.cell(tot_dr, 6, f"=SUM(F{start_r}:F{last_r})")
        ws_summary.cell(tot_dr, 7, f"='{source_sheet_name}'!{col_billed_letter}{statement_total_row}")
        ws_summary.cell(tot_dr, 8, f"=ROUND(F{tot_dr}-G{tot_dr}, 3)")

        for c_col in range(1, 11):
            cell = ws_summary.cell(tot_dr, c_col)
            cell.font = font_calc_hdr
            cell.fill = fill_total_row
            cell.border = total_border
            if c_col in range(3, 9):
                cell.number_format = num_fmt_vol
                cell.alignment = Alignment(horizontal="right", vertical="center")

        # Условное форматирование на колонку H (Отклонение)
        diff_rng = f"H6:H{tot_dr}"
        ws_summary.conditional_formatting.add(
            diff_rng,
            CellIsRule(operator='equal', formula=['0'], stopIfTrue=True, fill=green_fill, font=green_font)
        )
        ws_summary.conditional_formatting.add(
            diff_rng,
            CellIsRule(operator='notEqual', formula=['0'], stopIfTrue=True, fill=red_fill, font=red_font)
        )

        # Ширина столбцов дашборда
        dash_widths = {
            'A': 6,
            'B': 38,
            'C': 22,
            'D': 22,
            'E': 22,
            'F': 24,
            'G': 24,
            'H': 18,
            'I': 22,
            'J': 24
        }
        for col_l, width in dash_widths.items():
            ws_summary.column_dimensions[col_l].width = width

        if progress_callback:
            progress_callback(90, f"Сохранение файла в папку {subfolder_name}...")

        check_cancelled()
        # Безопасное сохранение книги
        final_saved_path, save_warning = safe_save_workbook(wb, target_path)
        wb.close()

        tot_day = sum(p['day'] for p in preview_data)
        tot_night = sum(p['night'] for p in preview_data)
        tot_odn = sum(p['odn'] for p in preview_data)
        tot_all = tot_day + tot_night + tot_odn
        stmt_total_val = billed_value(statement_total_row) if statement_total_row else tot_all
        balance_diff = round(tot_all - stmt_total_val, 3)

        if progress_callback:
            progress_callback(100, f"Готово! Сохранен в: {os.path.basename(target_dir)}")

        return {
            "success": True,
            "consumer": consumer_name,
            "contract": contract_num,
            "period": period_str,
            "subfolder_name": subfolder_name,
            "target_dir": target_dir,
            "target_path": final_saved_path,
            "warning": save_warning,
            "houses_count": len(houses),
            "total_day": tot_day,
            "total_night": tot_night,
            "total_odn": tot_odn,
            "total_simple": tot_odn,
            "total_all": tot_all,
            "statement_total": stmt_total_val,
            "balance_diff": balance_diff,
            "balance_ok": abs(balance_diff) < 0.001,
            "preview_rows": preview_data,
            "columns_used": cols
        }

    finally:
        if value_wb is not None:value_wb.close()
        wb.close()
