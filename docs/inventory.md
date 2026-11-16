# Инвентарь legacy/pyqt и контракты для миграции

Источник: `legacy/pyqt/` (снапшот v2.2.3/2.2.4, коммит `a40a177`).
Ссылки — `legacy/pyqt/<file>:<line>`. Новый стек (`crates/`, `src-tauri/`, `apps/ui/`) пока не создан.

## 1. Модули

| Файл | Роль | Судьба |
|---|---|---|
| `app_gui.py` | PySide6 UI: `AlgorithmHelpDialog`, `CalculationWorker(QThread)`, `TNSEnergyStudioWindow`, `main()` | → React UI (`apps/ui`), design parity |
| `core_engine.py` | Обработка ведомостей: `safe_float`, `classify_zone`, `resolve_columns`, `safe_save_workbook`, `detect_statement_type`, `process_statement` | → `crates/tns-core` + `crates/tns-excel` |
| `tns_input.py` | Разбор макета: `normalize_header`, `row_type`, `resolve_layout`, `total_row`, `numeric_value`, `extract_metadata` | → `crates/tns-core` |
| `sync_manager.py` | `S3Config`, `DatabaseManager`, `WindowsUpdateDeployer`, `S3PushEngine`, воркеры sync/update | БД → `crates/tns-db`; updater → Tauri; S3/sync → удалить |
| `cloud_sync.py` | S3-синхронизация БД | удалить |
| `ui_sync_components.py` | UI синхронизации/апдейта (`S3StatusBadge`, диалоги) | sync-часть удалить; updater UI → Tauri |
| `database_safety.py` | `validate_database`, `stage_database` | → `crates/tns-db` |
| `app_self_test.py` | Офлайн-самопроверка, синтетическая ведомость | → `tests/parity` (шаблон фикстуры) |
| `windows_update.py`, `update_helper.py` | Деплой zip-апдейта | заменить Tauri updater |
| `publish_release.py`, `latest.json` | Публикация в Yandex Object Storage | заменить GitHub Actions + Releases |
| `VERSION_2_2_*.txt`, `*.spec`, иконки | Метаданные/сборка | перенести в новый билд по мере необходимости |

## 2. Контракты ядра

### `tns_input.py`

- `normalize_header(value)` — lower, `ё→е`, убрать `_x000d_`, дефисы внутри слов, оставить `[a-zа-я0-9]`.
- `row_type(value)` — `100/101/102` → int, иначе `None`.
- `resolve_layout(ws)` — сканирует до 250 строк × 200 колонок; типовая колонка — где есть 100 и (101 или 102); заголовки ищутся по `normalize_header`; ошибки:
  - `Неоднозначная колонка типов строк. Проверьте заголовок «Тип».`
  - `Не найдены строки домов и приборов (типы 100/101/102). Выберите исходную ведомость ТНС.`
  - `Не найдена колонка «Начисленный объем». Нельзя безопасно выбрать расход по номеру столбца.`
  - `Не найдена колонка «Зона тарифа». Проверьте исходную ведомость.`
- Колонки по умолчанию: `col_type=1, col_point_num=3, col_point_name=4, col_meter_num=5, col_zone=9, col_sub_type=10, col_read_start=12, col_read_end=13, col_diff=15, col_coeff=16, col_main_exp=17, col_sub_deduct=23, col_billed_vol=28`.
- `total_row(ws,row,cols)` — «итого»/«всего» в колонках `col_type+1 .. col_point_name`.
- `numeric_value(value, coordinate)` — пусто/`-`/`—` → 0.0; пробелы/`\xa0`/`,` нормализуются; ошибки:
  - `В ячейке {coordinate} некорректный расход: {value!r}.`
  - `В ячейке {coordinate} расход не является конечным числом.`
- `extract_metadata(ws)` → `(consumer, contract, period)`; consumer ищет «южныйгород»/«южныйдом», contract — `23110604327`/`23110603789`, period — месяц + год.

### `core_engine.py`

- `safe_float(val, default=0.0)` — никогда не бросает; `None`/пусто/`-`/`—`/`none`/`null`/`nan` → default; запятая → точка.
- `classify_zone(zone_str)` — `day`: день/дн/пик/полупик/Т1/Т-1; `night`: ночь/ноч/Т2/Т-2; `odn`: ОДН/общедомовые/места общего пользования/без дифференциации; остальное → `odn`.
- `safe_save_workbook(wb, target_path)` — сохраняет во временный файл, затем `os.replace`; при `PermissionError` — fallback-имя с меткой времени; возвращает `(path, warning)`.
- `detect_statement_type(filepath)` — sha256 + `lru_cache`; `gorod` ищется первым, затем `dom`; fallback по договорам; возвращает `(type, consumer, contract)`.
- `process_statement(source_path, output_dir=None, custom_filename=None, month=None, year=None, progress_callback=None, cancel_callback=None)`:
  - прогресс: `5` чтение, `15` анализ, `35` найдено домов, `65` формулы, `90` сохранение, `100` готово;
  - листы: `Сводка по домам`, `Ведомость ЭП`;
  - результат: `success, consumer, contract, period, subfolder_name, target_dir, target_path, warning, houses_count, total_day, total_night, total_odn, total_simple, total_all, statement_total, balance_diff, balance_ok, preview_rows, columns_used`;
  - ошибки: `Не найдены дома...`, `Не найдена итоговая строка ведомости «Итого»...`, `Формула в {coordinate} не пересчитана...`, `Расчет отменен пользователем.`
- Excel-стили: Segoe UI 9/10/13; заливки `FFF2CC`, `D9E1F2`, `E2EFDA`, `F2F2F2`, `BDD7EE`, `F2F4F7`, `1F4E79`; границы thin `D3D3D3`, double `1F4E79`; формат `#,##0.000`; freeze `C6`; условное форматирование `H6:H...`.

## 3. БД (legacy `sync_manager.py:init_db`)

- `organizations(id, name, contract_number, slug)`
- `houses(id, org_contract, address, meters_count_active, meters_count_reserve, ...)`
- `tariffs(id, zone_code, zone_name, rate_rub, note)`
- `calculation_history(id, ...)`
- `sync_metadata` — **не портируется** (sync удалён).
- Seed: `ООО «Южный Дом» / 23110603789 / dom`, `ООО «Южный Город» / 23110604327 / gorod`; тарифы `day 7.15`, `night 4.22`, `odn 6.45`.
- Бэкап: SQLite backup API → `backups/tns_database_backup_<timestamp>.sqlite`; валидация/стейджинг — `database_safety.py`.

## 4. Tauri-команды v1 (проект, финализирует `tauri-shell`)

`detect_statement`, `process_statement`, `history_list`, `config_get`, `open_file`, `open_folder`, `backup_db`, `update_check`.
JSON-схемы входов/выходов — по legacy-структурам; `process_statement` стримит прогресс/отмену.

## 5. UI-токены (QSS `app_gui.py:apply_theme`)

- Фон `#0F172A`, панели `#1E293B`, границы `#334155`, текст `#F8FAFC`, muted `#94A3B8`.
- Primary `#2563EB` (hover `#1D4ED8`, pressed `#1E40AF`, disabled `#475569`), accent `#38BDF8`.
- Успех `#10B981`, ошибка `#EF4444` / `#7F1D1D`, warning `#F59E0B`, фиолетовый `#818CF8`.
- Шрифт Segoe UI, 11–17px, веса 500–800; скругления 4/8/12px.
- Окно 1280×880, минимум 1060×720; вкладки «Ведомость (дом)» / «Ведомость (город)»; кнопка «Облако» удаляется.

## 6. Удаляется вместе с Yandex

`cloud_sync.py`, `S3Config`, `S3PushEngine`, `CloudDatabaseSync`, `S3StatusBadge`, `sync_metadata`, `latest.json` с Yandex URL, `publish_release.py`, `windows_update.py`, `update_helper.py` — заменяются GitHub Releases + Tauri updater.
