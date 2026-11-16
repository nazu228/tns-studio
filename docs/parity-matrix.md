# Матрица паритета legacy → Rust / React / Tauri

Статусы: **не портировано** — функция есть в legacy, порта нет; **готово** — порт и проверка есть; **удалено** — не переносится по решению (sync/Yandex).

## Ядро

| Legacy | Контракт | Порт | Статус | Проверка |
|---|---|---|---|---|
| `tns_input.py:5` `normalize_header` | нормализация заголовков | `tns-core` | портировано + тесты | unit-тесты |
| `tns_input.py:10` `row_type` | 100/101/102 | `tns-core` | портировано + тесты | unit-тесты |
| `tns_input.py:16` `resolve_layout` | колонки + 4 ошибки | `tns-core` | не портировано | golden-фикстуры |
| `tns_input.py:66` `total_row` | «итого/всего» | `tns-core` | портировано + тесты | unit-тесты |
| `tns_input.py:69` `numeric_value` | парсинг чисел + 2 ошибки | `tns-core` | портировано + тесты | unit-тесты |
| `tns_input.py:76` `extract_metadata` | consumer/contract/period | `tns-core` | не портировано | golden-фикстуры |
| `core_engine.py:19` `safe_float` | пробелы/запятые/дефисы | `tns-core` | портировано + тесты | unit-тесты |
| `core_engine.py:37` `classify_zone` | day/night/odn | `tns-core` | портировано + тесты | unit-тесты |
| `core_engine.py:68` `safe_save_workbook` | атомарная запись + fallback | `tns-excel` | портировано + тесты | unit-тест |
| `core_engine.py:92` `detect_statement_type` | sha256 + dom/gorod | `tns-core` | не портировано | golden-фикстуры |
| `core_engine.py:125` `process_statement` | прогресс 5/15/35/65/90/100, 2 листа, формулы, result | `tns-core` + `tns-excel` | не портировано | golden-тесты |
| Excel-стили `core_engine.py:276–331` | Segoe UI, заливки, границы, `#,##0.000` | `tns-excel` | не портировано | xlsx-сигнатура |

## БД

| Legacy | Контракт | Порт | Статус | Проверка |
|---|---|---|---|---|
| `sync_manager.py:295` `init_db` | organizations/houses/tariffs/calculation_history | `tns-db` | портировано + тесты | схема + seed |
| `sync_manager.py:397` `create_backup` | локальный бэкап | `tns-db` | портировано + тесты | тест бэкапа |
| `sync_manager.py:441` `record_calculation` | история расчётов | `tns-db` | портировано + тесты | тест |
| `database_safety.py:8` | validate | `tns-db` | портировано + тесты | тест валидации |

## UI

| Legacy | Контракт | Порт | Статус | Проверка |
|---|---|---|---|---|
| `app_gui.py:250` окно | 1280×880, min 1060×720, заголовок | `apps/ui` | не портировано | скриншот |
| `app_gui.py:532` вкладка «дом» | таблица, карточки, итоги | `apps/ui` | не портировано | скриншот |
| `app_gui.py:550` вкладка «город» | таблица, карточки, итоги | `apps/ui` | не портировано | скриншот |
| `app_gui.py:311–321` кнопка «Облако» | sync UI | — | удалено | — |
| `app_gui.py:26` `AlgorithmHelpDialog` | две вкладки помощи | `apps/ui` | не портировано | скриншот |
| `app_gui.py:160` `CalculationWorker` | прогресс/отмена | Tauri events | не портировано | e2e |
| `app_gui.py:925` QSS | токены Cobalt Dark | `apps/ui` | не портировано | визуальный diff |

## Обновления

| Legacy | Контракт | Порт | Статус | Проверка |
|---|---|---|---|---|
| `latest.json` + Yandex URL | манифест апдейта | GitHub Releases `latest.json` | не портировано | проверка манифеста |
| `publish_release.py` | публикация в Yandex | GitHub Actions | не портировано | dry-run workflow |
| `windows_update.py` / `update_helper.py` | zip-апдейт | Tauri updater + minisign | не портировано | тест обновления |

## Parity-харнесс

| Артефакт | Статус | Проверка |
|---|---|---|
| `tests/parity/scripts/gen_fixtures.py` | готово | 3 фикстуры (dom/gorod/march) |
| `tests/parity/scripts/gen_golden.py` | готово | golden xlsx + JSON |
| `tests/parity/tests/test_parity.py` | готово | `7 passed` |
| `tests/parity/screenshots` | готово | 5 PNG: empty, help, dom, gorod, error |
| `tests/parity/benchmarks` | не начато | нужен замер legacy |

Итого: 61 строка в полной версии (52 «не портировано», 9 «удалено»); в этой сокращённой — ключевые 24 строки. Статусы обновляются после каждого порта.
