# TNS Energy Studio — миграция на Rust + React + Tauri

TNS Energy Studio — десктопное приложение для обработки ведомостей энергосбыта
(Excel → расчёт → Excel). Текущая версия написана на Python/PySide6.

Этот репозиторий — рабочая площадка миграции на новый стек:

- **Rust core** (логика, SQLite, Excel, обновления)
- **React + TypeScript + Vite** (UI, design parity с текущим приложением)
- **Tauri 2** (десктопная оболочка)
- **GitHub Releases** (обновления вместо Yandex Object Storage)

## Структура

```
legacy/pyqt/        # эталон: текущий исходник PySide6 (не менять, это оракул)
crates/             # Rust workspace (создаётся в ходе миграции)
src-tauri/          # Tauri shell (создаётся в ходе миграции)
apps/ui/            # Vite + React UI (создаётся в ходе миграции)
tests/parity/       # pytest: golden-файлы, скриншоты legacy, контракты
docs/               # план миграции, инвентарь, матрица паритета
.github/workflows/  # CI: build, test, release на GitHub
```

## Зафиксированные решения

Полный список — в `docs/TNS_MIGRATION_PLAN.md`. Коротко:

- UI — React/TS (не Rust); ядро — Rust; оболочка — Tauri 2.
- Визуальный паритет: near-pixel (та же компоновка, цвета, шрифты, поведение; ±2px).
- Данные — только локальная SQLite + локальные бэкапы. Облачная синхронизация (S3/Yandex) удалена.
- Обновления — только GitHub: Releases + `latest.json` + Tauri updater. Yandex не используется.
- Подписи: minisign (updater) + Authenticode (Windows).
- No-code слой — позже. TMZ и WaterMetrics — после TNS.

## Как запустить legacy-эталон

```powershell
python legacy/pyqt/app_gui.py
```

Нужен Python 3.11+ с PySide6, openpyxl. База создаётся и заполняется автоматически при первом запуске.

## Parity-харнесс (legacy — оракул)

```powershell
python tests/parity/scripts/gen_fixtures.py
python tests/parity/scripts/gen_golden.py
python tests/parity/scripts/gen_screenshots.py
python -m pytest tests/parity -q
```

Сейчас: 3 фикстуры (dom/gorod/march), golden-выходы legacy, 5 скриншотов
(`tests/parity/screenshots/`) и 7 зелёных тестов.
`legacy/pyqt/` не изменяется: проверка `git diff --exit-code origin/rust-migration -- legacy/pyqt`.

## Rust core

```powershell
.\scripts\cargo.ps1 check --manifest-path crates/tns-core/Cargo.toml
.\scripts\cargo.ps1 test  --manifest-path crates/tns-core/Cargo.toml
.\scripts\cargo.ps1 test  --manifest-path crates/tns-db/Cargo.toml
.\scripts\cargo.ps1 test  --manifest-path crates/tns-excel/Cargo.toml
```

Портированы чистые функции `normalize_header`, `row_type`, `safe_float`,
`numeric_value`, `classify_zone`, `total_row` (6 тестов) и локальная БД
`tns-db`: схема legacy, seed, история, upsert домов, бэкап, валидация
(4 теста). `cargo test` требует MSVC Build Tools (`link.exe`).

## Tauri shell

```powershell
.\scripts\cargo.ps1 check --manifest-path src-tauri/Cargo.toml
```

Tauri 2, окно 1280×880, `frontendDist` на `apps/ui/dist`. Команды:
`history_list`, `backup_db`, `open_file`, `open_folder`, `config_get`,
`detect_statement`, `process_statement`, `update_check`.
`detect_statement`/`process_statement` пока заглушки до Excel-порта.

## React UI (Vite)

```powershell
cd apps/ui
npm install
npm run typecheck
npm run build
npm run dev
```

Сейчас это скелет главного окна TNS с design parity: шапка, режимы расчёта,
выбор источника, месяц/год, карточки, вкладки «Дом»/«Город», таблица, итоги,
справка. Кнопка «Облако» и S3-бейдж удалены по плану. Данные — моковые,
Tauri-команды подключим после Rust-ядра.

## Полная верификация

```powershell
.\scripts\verify.ps1
```

Скрипт ставит зависимости `apps/ui`, если `node_modules` отсутствует (в свежем worktree его нет
и `tsc` не находится), затем гоняет `cargo test`/`check`, parity-тесты, `npm typecheck`/`build`
и проверяет, что `legacy/pyqt` и `tests/parity` не изменены.

## Handoff и карта кода

- `docs/HANDOFF_PROMPT.md` — полный промпт для нового чата/агента.
- `graphify-out/GRAPH_REPORT.md` — карта кода (719 узлов, 1511 рёбер, 36 сообществ).
- `graphify-out/graph.html` — интерактивная карта.
- `graphify-out/graph.json` — граф для `graphify query/path/explain`.

```powershell
graphify query "как process_statement связан с tns-db?"
graphify update .   # после изменений кода
```

## Статус миграции

- `main` — legacy-снапшот.
- `rust-migration` — план миграции.
- `parity-harness` — фикстуры, golden, скриншоты и тесты (готово).
- `apps/ui` — React-скелет главного окна (готово).
- Rust-ядро и Tauri-оболочка — следующий этап; нужен Rust toolchain + MSVC Build Tools.
