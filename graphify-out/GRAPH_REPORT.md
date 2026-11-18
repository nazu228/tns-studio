# Graph Report - tns-studio  (2026-11-18)

## Corpus Check
- 74 files · ~71,057 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .ico 2, (none) 1, .css 1)

## Summary
- 1020 nodes · 2107 edges · 60 communities (40 shown, 20 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 203 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `20898788`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sync_manager.py
- process.rs
- process_statement
- tns-db/src/lib.rs
- TNSEnergyStudioWindow
- package.json
- DatabaseManager
- test_parity.py
- S3Config
- tns-excel/src/lib.rs
- columns
- compilerOptions
- CloudSyncDialog
- tauri.conf.json
- TNS Energy Studio — полный план миграции на Rust + React + Tauri
- App.tsx
- DiagnosticService
- gen_fixtures.py
- Статус миграции TNS Energy Studio
- ui_sync_components.py
- CheckUpdatesWorker
- DownloadUpdateWorker
- SyncPushWorker
- tns-core
- dom_april_2026_d7804be7.md
- dom_march_2026_705de24c.md
- gorod_april_2026_d0ca431b.md
- golden/manifest.json
- ProcessOptions<'a>
- dom_april_2026_394e4478.md
- dom_march_2026_e13491e6.md
- gorod_april_2026_78d6ee3c.md
- HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri
- output_style.rs
- TnsError
- dependencies
- style_statement
- scripts
- ExcelError
- data.ts
- with
- with
- S3Config
- UpdateModalDialog
- aligned
- AlgorithmHelpDialog
- publish_release.py
- TNS Energy Studio — миграция на Rust + React + Tauri
- DiagnosticService
- StatementKind
- S3PushEngine
- Статус миграции TNS Energy Studio
- default.json
- ResilientHttpClient
- update_helper.py

## God Nodes (most connected - your core abstractions)
1. `TNSEnergyStudioWindow` - 40 edges
2. `CloudSyncDialog` - 35 edges
3. `process_statement()` - 34 edges
4. `xlsx_signature()` - 34 edges
5. `S3Config` - 29 edges
6. `process_statement()` - 26 edges
7. `DatabaseManager` - 25 edges
8. `SyncError` - 24 edges
9. `main()` - 23 edges
10. `App()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `2026-11-17 — Slice 1 gates the workbook through the layout signature` --references--> `process_statement()`  [INFERRED]
  DECISIONS.md → legacy/pyqt/core_engine.py
- `2026-11-18 — Tauri IPC contract for statement commands` --references--> `process_statement()`  [INFERRED]
  DECISIONS.md → legacy/pyqt/core_engine.py
- `Срез 3 — Tauri commands (готов)` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `Срез 6 — e2e/smoke (готов)` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `4. Tauri-команды v1 (проект, финализирует `tauri-shell`)` --references--> `process_statement()`  [INFERRED]
  docs/inventory.md → legacy/pyqt/core_engine.py

## Import Cycles
- 2-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/lib.rs`
- 2-file cycle: `crates/tns-core/src/output.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs`
- 2-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/lib.rs`
- 4-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/layout.rs`

## Communities (60 total, 20 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.14
Nodes (8): _Blob, credentials(), _dpapi(), run_diagnostics(), save_credentials(), stage_database(), validate_database(), get_executable_path()

### Community 1 - "process.rs"
Cohesion: 0.15
Nodes (21): assert_number(), assert_preview_rows(), billed_value(), cancellation_has_legacy_message(), cell(), custom_filename_is_applied(), emit(), fill_rgb() (+13 more)

### Community 2 - "process_statement"
Cohesion: 0.20
Nodes (21): 4. Текущее состояние (факты), Чего ещё нет, 1. Модули, Ядро, Phase 1 — скелет, 2. Текущее состояние (эталон), classify_zone(), detect_statement_type() (+13 more)

### Community 3 - "tns-db/src/lib.rs"
Cohesion: 0.10
Nodes (15): backs_up_and_validates(), CalculationRecord, creates_legacy_schema_and_seed(), Database, DbError, Io, Message, Sql (+7 more)

### Community 4 - "TNSEnergyStudioWindow"
Cohesion: 0.06
Nodes (5): main(), TNSEnergyStudioWindow, S3StatusBadge, ToastManager, ToastNotification

### Community 5 - "package.json"
Cohesion: 0.16
Nodes (15): devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0, typescript@^7.0.2, vite@^8.3.8, @vitejs/plugin-react@^6.3.0, name, private (+7 more)

### Community 6 - "DatabaseManager"
Cohesion: 0.12
Nodes (3): calculate_file_sha256(), DatabaseManager, DatabaseViewerDialog

### Community 7 - "test_parity.py"
Cohesion: 0.05
Nodes (53): 2026-11-17 — Full xlsx signature is now the release gate, 2026-11-17 — Narrow umya xlsx presentation sanitizers, 2026-11-17 — Output writer assumes the statement is sheet 0, 2026-11-17 — Slice 1 gates the workbook through the layout signature, 2026-11-17 — The xlsx signature is the shared parity oracle, 2026-11-17 — umya coalesces equal adjacent column widths, 2026-11-18 — Build the UI before Tauri checks in CI, 2026-11-18 — Release 0.2.0 builds in the workspace target (+45 more)

### Community 8 - "S3Config"
Cohesion: 0.07
Nodes (29): Args, main(), next_value(), parse_args(), run(), AppState, backup_db(), cancel_statement() (+21 more)

### Community 9 - "tns-excel/src/lib.rs"
Cohesion: 0.11
Nodes (18): ExcelResult, FALLBACK_WARNING, fixture(), mark_inline_string(), marks_empty_cell_as_inline_string(), read(), reads_fixture_values(), safe_save() (+10 more)

### Community 10 - "columns"
Cohesion: 0.11
Nodes (18): columns, billed, coeff, diff, end, main, meter, name (+10 more)

### Community 11 - "compilerOptions"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+9 more)

### Community 13 - "tauri.conf.json"
Cohesion: 0.08
Nodes (24): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+16 more)

### Community 14 - "TNS Energy Studio — полный план миграции на Rust + React + Tauri"
Cohesion: 0.12
Nodes (16): 10. Задачи первого захода squad (Phase 0–1), 1. Зафиксированные решения (с заказчиком), 3. Целевая архитектура, 4. Визуальный паритет (критерий приёмки UI), 5. Фазы, 6. Обновления через GitHub (замена Yandex), 8. Риски и fallback, 9. Верификация (gate) (+8 more)

### Community 15 - "App.tsx"
Cohesion: 0.10
Nodes (36): App(), CalculationPlan, clamp(), describeDetect(), energy(), errorText(), fmt(), HelpTab (+28 more)

### Community 16 - "DiagnosticService"
Cohesion: 0.17
Nodes (9): CloudDatabaseSync, config_data(), database_differs(), _prefix(), PublicHttp, scoped_url(), SyncConflict, SyncError (+1 more)

### Community 17 - "gen_fixtures.py"
Cohesion: 0.33
Nodes (6): build_statement(), comma_fmt(), fmt(), main(), rnd(), sha256_file()

### Community 18 - "Статус миграции TNS Energy Studio"
Cohesion: 0.23
Nodes (18): column_letter(), cell_formula(), cell_number(), cell_text(), HouseStats, open_statement(), set_column_widths(), set_frozen_at_c6() (+10 more)

### Community 19 - "ui_sync_components.py"
Cohesion: 0.12
Nodes (3): CheckUpdatesWorker, DownloadUpdateWorker, SyncPullWorker

### Community 20 - "CheckUpdatesWorker"
Cohesion: 0.21
Nodes (12): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+4 more)

### Community 21 - "DownloadUpdateWorker"
Cohesion: 0.14
Nodes (11): run(), atomic_json(), prepare_update(), unpack_release(), fixtures_manifest(), golden_manifest(), parity_dirs(), ParityDirs (+3 more)

### Community 22 - "SyncPushWorker"
Cohesion: 0.15
Nodes (17): classifies_zones(), classify_zone(), detects_total_rows(), is_word_char(), normalize_header(), normalizes_russian_headers(), numeric_value(), numeric_value_matches_legacy_contract() (+9 more)

### Community 23 - "tns-core"
Cohesion: 0.60
Nodes (5): tns-core, tns-db, tns-excel, tns-parity, tns-studio

### Community 36 - "HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri"
Cohesion: 0.11
Nodes (18): 10. Graphify (карта кода), 11. Первый шаг нового чата, 1. Роль, 2. Что за проект, 3. Зафиксированные решения (не менять без пользователя), 5. Карта репозитория, 6. Что делать дальше (порядок), 7. Жёсткие ограничения (+10 more)

### Community 37 - "output_style.rs"
Cohesion: 0.09
Nodes (18): BORDER_COLOR, COLOR_GREEN, COLOR_RED, conditional_rule(), deviation_formatting(), FILL_CALC_ROW, FILL_DAY, FILL_GREEN (+10 more)

### Community 38 - "TnsError"
Cohesion: 0.29
Nodes (5): TnsError, InvalidNumber, Message, NonFinite, check_cancel()

### Community 39 - "dependencies"
Cohesion: 0.22
Nodes (9): dependencies, react@^19.3.1, react-dom@^19.3.1, @tauri-apps/api@^2.12.5, @tauri-apps/plugin-dialog@^2.8.4, react, react-dom, @tauri-apps/api (+1 more)

### Community 40 - "style_statement"
Cohesion: 0.25
Nodes (10): apply_box_border(), apply_total_border(), argb(), font(), meter_style(), set_side(), solid_fill(), style_statement() (+2 more)

### Community 41 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, preview, typecheck

### Community 42 - "ExcelError"
Cohesion: 0.24
Nodes (6): ExcelError, Io, Message, Read, Write, zip_error()

### Community 44 - "with"
Cohesion: 0.05
Nodes (37): concurrency, cancel-in-progress, group, GITHUB_TOKEN, TAURI_SIGNING_PRIVATE_KEY, TAURI_SIGNING_PRIVATE_KEY_PASSWORD, WINDOWS_CERTIFICATE, WINDOWS_CERTIFICATE_PASSWORD (+29 more)

### Community 45 - "with"
Cohesion: 0.10
Nodes (20): jobs, verify, name, on, pull_request, push, permissions, contents (+12 more)

### Community 49 - "AlgorithmHelpDialog"
Cohesion: 0.11
Nodes (7): Parity-харнесс, UI, БД, Матрица паритета legacy → Rust / React / Tauri, Обновления, AlgorithmHelpDialog, CalculationWorker

### Community 50 - "publish_release.py"
Cohesion: 0.19
Nodes (9): S3Store, sha256(), validate_manifest(), build_if_needed(), main(), release_files(), signature(), constant() (+1 more)

### Community 51 - "TNS Energy Studio — миграция на Rust + React + Tauri"
Cohesion: 0.18
Nodes (10): Handoff и карта кода, Legacy-эталон, Parity-харнесс, TNS Energy Studio — миграция на Rust + React + Tauri, Updater и GitHub Releases, Быстрый старт, Ветки, Зафиксированные решения (+2 more)

### Community 53 - "StatementKind"
Cohesion: 0.40
Nodes (4): StatementKind, Dom, Gorod, Unknown

### Community 55 - "S3PushEngine"
Cohesion: 0.17
Nodes (10): 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), 6. Удаляется вместе с Yandex, `core_engine.py`, `tns_input.py`, Инвентарь legacy/pyqt и контракты для миграции (+2 more)

### Community 56 - "Статус миграции TNS Energy Studio"
Cohesion: 0.22
Nodes (8): Phase 0 — parity-база, Phase 2 — release 0.2.0 (подготовка), В работе, Известные девиации, Проверки, Сделано, Следующие шаги, Статус миграции TNS Energy Studio

### Community 57 - "default.json"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 59 - "update_helper.py"
Cohesion: 0.43
Nodes (3): _hash(), install(), wait_pid()

## Knowledge Gaps
- **12 isolated node(s):** `Dom`, `Gorod`, `Unknown`, `Day`, `Night` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 373 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_statement()` connect `process_statement` to `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri`, `test_parity.py`, `TNS Energy Studio — полный план миграции на Rust + React + Tauri`, `AlgorithmHelpDialog`, `ui_sync_components.py`, `TNS Energy Studio — миграция на Rust + React + Tauri`, `DownloadUpdateWorker`, `S3PushEngine`, `Статус миграции TNS Energy Studio`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Dom`, `Gorod`, `Unknown` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1354679802955665 - nodes in this community are weakly interconnected._
- **Why does `9. Известные ловушки (проверено на практике)` connect `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri` to `process_statement`, `test_parity.py`, `App.tsx`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `CloudSyncDialog` (e.g. with `TNSEnergyStudioWindow` and `CheckUpdatesWorker`) actually correct?**
  _`CloudSyncDialog` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.14623655913978495 - nodes in this community are weakly interconnected._