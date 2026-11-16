# TNS Energy Studio — полный план миграции на Rust + React + Tauri

Версия 1.0. Источник истины для всех исполнителей (людей и агентов).

---

## 1. Зафиксированные решения (с заказчиком)

| # | Решение | Значение |
|---|---|---|
| 1 | Ядро | Rust + Tauri 2 |
| 2 | UI | React + TypeScript + Vite (десктоп). UI — не Rust |
| 3 | Визуал | Design parity, near-pixel: та же компоновка, кнопки на местах, цвета/шрифты/размеры те же, допуск геометрии ±2px. Редизайн запрещён |
| 4 | Данные | Только локальная SQLite + локальные бэкапы. Облачная синхронизация удаляется |
| 5 | Yandex | Уходит полностью (Object Storage для апдейтов и sync) |
| 6 | Обновления | GitHub only: GitHub Releases + `latest.json` + Tauri updater |
| 7 | Репозиторий | Публичный `nazu228/tns-studio` |
| 8 | Подписи | minisign (updater) + Authenticode (Windows) |
| 9 | Python | Переходный. Эталон остаётся оракулом; конечная точка — Python = 0 |
| 10 | No-code | Позже (Phase 6+), на базе токенов/вариантов; Puck/Onlook как основа |
| 11 | Порядок | TNS первым. TMZ (с 1С UIA spike) и WaterMetrics — после |
| 12 | Стиль кода | Чистые функции, golden-тесты, без галлюцинаций: неоднозначное поведение сверять с `legacy/pyqt/` |

---

## 2. Текущее состояние (эталон)

Снапшот развёрнутой версии v2.2.3/2.2.4 лежит в `legacy/pyqt/` (не менять).

| Файл | Размер | Роль | Судьба |
|---|---|---|---|
| `app_gui.py` | 62 КБ | PySide6 UI: `AlgorithmHelpDialog`, `CalculationWorker(QThread)`, `TNSEnergyStudioWindow` | → React UI (`apps/ui`) |
| `core_engine.py` | 34 КБ | Обработка ведомостей (openpyxl): `safe_float`, `classify_zone`, `resolve_columns`, `safe_save_workbook`, `detect_statement_type`, `process_statement` | → Rust (`crates/tns-core`) |
| `tns_input.py` | 5 КБ | Разбор макетов: `normalize_header`, `row_type`, `resolve_layout`, `total_row`, `numeric_value`, `extract_metadata` | → Rust (`crates/tns-core`) |
| `ui_sync_components.py` | 52 КБ | UI синхронизации/апдейта (S3StatusBadge и т.п.) | sync-часть удалить; апдейт → Tauri plugin |
| `sync_manager.py` | 33 КБ | S3 конфиг, `DatabaseManager`, `WindowsUpdateDeployer`, `S3PushEngine` | расщепить: БД → `crates/tns-db`, апдейтер → Tauri, S3 → удалить |
| `cloud_sync.py` | 25 КБ | S3-синхронизация БД | удалить |
| `database_safety.py` | 1 КБ | Валидация/стейджинг БД | → Rust (`crates/tns-db`) |
| `app_self_test.py` | 1 КБ | Самопроверка | → Rust/tests |
| `windows_update.py`, `update_helper.py` | 9 КБ | Деплой zip-апдейта | заменить Tauri updater |
| `publish_release.py` | 8 КБ | Публикация релизов в Yandex | заменить GitHub Actions |
| `latest.json`, `sync_config.json` | — | Манифест апдейта (Yandex URL) | заменить на GitHub Releases `latest.json` |

**БД** `database/tns_database.sqlite` (локальная): таблицы `organizations`, `houses`, `tariffs`, `calculation_history`, `sync_metadata`. Seed выполняется при первом запуске (`init_db`). `sync_metadata` уходит вместе с sync.

**Поведение ядра** (важно для parity): `process_statement(source_path, output_dir, custom_filename, month, year, progress_callback, cancel_callback)` читает ведомость, определяет тип (`dom`/`gorod`), считает, пишет xlsx через `safe_save_workbook` (атомарно, с fallback-именем при PermissionError).

---

## 3. Целевая архитектура

```
tns-studio/
  legacy/pyqt/          # эталон, оракул (read-only)
  crates/
    tns-core/           # чистые функции: tns_input + core_engine (без Qt, без openpyxl)
    tns-db/             # rusqlite: схема, seed, backup, calculation_history, валидация
    tns-excel/          # чтение/запись xlsx (calamine / rust_xlsxwriter)
    tns-updater/        # манифест GitHub Releases + конфиг Tauri updater
  src-tauri/            # Tauri 2 shell: окно, команды, иконка, updater
  apps/ui/              # Vite + React + TS: экраны, токены, компоненты
  tests/parity/         # pytest: golden xlsx, скриншоты legacy, контракты, бенчмарки
  docs/                 # план, инвентарь, матрица паритета
  .github/workflows/    # CI: test, build, release
```

Команды Tauri (v1): `detect_statement`, `process_statement`, `history_list`, `config_get`, `open_file`, `open_folder`, `backup_db`, `update_check`.

---

## 4. Визуальный паритет (критерий приёмки UI)

- Все элементы главного окна на местах: выбор папки/файла, месяц/год, директория вывода, кнопка «Сформировать ведомость», прогресс-бар, вкладки «Ведомость (дом)» / «Ведомость (город)», таблица результатов, итоги, строка статуса, «Открыть файл в Excel», «Открыть папку с файлом», диалог помощи.
- Геометрия в пределах ±2px на 100% масштабе; поведение hover/active/disabled/loading/error как в legacy.
- Цвета — точные токены из QSS; шрифты — те же family/size/weight; сглаживание может отличаться.
- Кнопка «Облако» удаляется (sync выпилен).
- Проверка: скриншоты legacy (pytest-qt `QWidget.grab()`) против Playwright-скриншотов React; diff как сигнал + ручное ревью.

---

## 5. Фазы

### Phase 0 — Инвентарь, фикстуры, замеры (первый заход squad)
- Инвентарь модулей и контрактов: `docs/inventory.md`, `docs/parity-matrix.md`.
- Фикстуры: 2–3 реальных ведомости xlsx + золотые выходные файлы из legacy Python + скриншоты всех окон/состояний.
- Бенчмарки legacy: старт, `process_statement` (время, память).
- Parity-харнесс `tests/parity` (pytest), запускающий legacy как оракул.

### Phase 1 — Скелет (первый заход squad)
- `crates/tns-core`: порт `tns_input.py` + `core_engine.py` с golden-тестами против фикстур.
- `crates/tns-db`: схема legacy (organizations/houses/tariffs/calculation_history), seed, backup, валидация; открывает существующую БД.
- `src-tauri`: Tauri 2 shell, команды ядра, иконка, запуск на Windows.
- `apps/ui`: порт главного окна (design parity), состояния загрузки/прогресса/ошибок.
- `crates/tns-updater` + `.github/workflows/release.yml`: GitHub Releases + `latest.json`, minisign-конфиг; без Yandex.
- **Гейт:** cargo check/test, golden-тесты, UI typecheck/build, Tauri запускается, legacy не сломан.

### Phase 2 — Полный UI
- Все диалоги, состояния, горячие клавиши; Playwright-сьют визуального паритета; responsive/DPI.
- **Гейт:** все экраны совпадают в пределах критериев §4.

### Phase 3 — Полное ядро и БД
- Все функции ядра, история расчётов, бэкап/restore, миграция данных из старой установки (`%LOCALAPPDATA%`), dual-run против legacy.
- **Гейт:** одинаковые выходы на всех фикстурах; бенчмарк не хуже legacy.

### Phase 4 — Упаковка и обновления
- Tauri bundler (NSIS/MSI), GitHub Actions release: сборка → подпись (minisign + Authenticode) → Releases + `latest.json`.
- Апгрейд со старой PySide-версии: перенос БД, удаление старого ярлыка, rollback.
- **Гейт:** чистая установка, апгрейд, офлайн, перезапуск.

### Phase 5 — Cutover
- Удаление Python из рабочего пути (эталон остаётся в `legacy/`), финальный релиз.
- **Гейт:** пользовательские сценарии полностью работают без Python.

### Phase 6+ — Дальше
- TMZ: 1С UIA spike на Rust → Excel → полная миграция.
- WaterMetrics: поиск исходников → миграция.
- No-code: токены/варианты + собственный редактор (Puck/Onlook как основа).

---

## 6. Обновления через GitHub (замена Yandex)

```
GitHub Actions (windows-latest)
  → cargo test / UI build / parity
  → tauri build (NSIS/MSI)
  → sign (Authenticode) + sign updater artifacts (minisign)
  → GitHub Release vX.Y.Z: installer + latest.json
App → GET latest.json → download → minisign verify → install → restart
```

Пример `latest.json` (Tauri updater):
```json
{
  "version": "3.0.0",
  "notes": "Первый релиз на Rust",
  "pub_date": "2026-12-01T00:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "<minisign signature>",
      "url": "https://github.com/nazu228/tns-studio/releases/download/v3.0.0/tns-studio_3.0.0_x64-setup.exe"
    }
  }
}
```

- Публичный репозиторий — токен в приложение не встраивается.
- Rollback: предыдущий релиз остаётся; манифест можно откатить.
- GitHub-only: зеркал нет (принятое решение); риск доступности GitHub в России принят.
- Authenticode обязателен, иначе SmartScreen.

---

## 7. Данные

- Локальная SQLite, та же схема; seed при первом запуске; WAL.
- Бэкапы локальные (как в legacy `create_backup`).
- Миграция с PySide-версии: старый файл БД открывается как есть; перед миграцией — бэкап.
- Облачная синхронизация удалена: `cloud_sync.py`, `S3PushEngine`, `CloudDatabaseSync`, `sync_metadata` — не реализовывать.

---

## 8. Риски и fallback

| Риск | Митигация | Fallback |
|---|---|---|
| openpyxl vs rust_xlsxwriter: расхождения форматирования/формул | golden-тесты по ячейкам и стилям | на время — Python-sidecar для генерации xlsx |
| QSS → CSS: отличия шрифтов/контролов | токены, Playwright diff, допуск ±2px | принять дизайн-девиации, зафиксировать в матрице |
| rusqlite миграция | стейджинг + бэкап (как legacy) | оставить Python для БД до Phase 3 |
| Tauri updater + подпись | minisign + Authenticode с первого релиза | без подписи — только manual download |
| Git-доступность GitHub из РФ | принято: GitHub-only | ручной релиз с локальной машины |
| AI-галлюцинации в порте логики | golden-тесты + оракул legacy | переписать модуль вручную |

---

## 9. Верификация (gate)

```powershell
cargo check --manifest-path crates/tns-core/Cargo.toml
cargo test --manifest-path crates/tns-core/Cargo.toml
cargo check --manifest-path src-tauri/Cargo.toml
python -m pytest tests/parity -q
cd apps/ui && bun install && bun run typecheck && bun run build
```

---

## 10. Задачи первого захода squad (Phase 0–1)

- **analyst**: инвентарь, контракты, фикстуры, скриншоты, бенчмарки, parity-харнесс.
- **executor**: Rust core (tns-core, tns-db, tns-excel), Tauri shell + команды, updater + CI.
- **visual-executor**: React UI главного окна (design parity), токены из QSS.
- **critic**: ревью каждого артефакта против этого плана; golden-тесты, визуальный паритет, отсутствие S3/Yandex, legacy не тронут.
