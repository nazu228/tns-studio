"""Opt-in offline verification of a packaged application; never opens a user's database."""
import json
from pathlib import Path
import tempfile
from openpyxl import Workbook
from core_engine import process_statement,classify_zone

def run(report_path=None):
    with tempfile.TemporaryDirectory(prefix='tns-self-test-') as folder:
        root=Path(folder);source=root/'input.xlsx'
        wb=Workbook();ws=wb.active
        for cell,value in {'D3':'Южный Город','D4':'23110604327','D5':'Апрель 2026 г.','A7':'Тип','C9':'Номер','D9':'Наименование','I7':'Зона тарифа','AB7':'Начисленный объём','A11':100,'C11':'Тест','AB11':42,'A12':101,'I12':'День','AB12':42,'A14':100,'B14':'Итого:','AB14':42}.items():ws[cell]=value
        wb.save(source);wb.close()
        result=process_statement(str(source),str(root/'result'),month='Апрель',year='2026')
        assert result['total_all']==42 and result['balance_ok']
        assert classify_zone('ОДН')=='odn'
        report={'packaged_calculation':'passed','result':42,'odn_classification':'passed'}
        if report_path:Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return 0
