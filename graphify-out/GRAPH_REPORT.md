# Graph Report - tns-studio  (2026-11-18)

## Corpus Check
- 70 files · ~66,911 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .ico 2, (none) 1, .css 1)

## Summary
- 942 nodes · 2033 edges · 47 communities (33 shown, 14 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 204 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8e6d4746`
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
- process_statement
- dependencies
- style_statement
- scripts
- ExcelError
- data.ts
- aligned
- publish_release.py
- default.json

## God Nodes (most connected - your core abstractions)
1. `TNSEnergyStudioWindow` - 40 edges
2. `CloudSyncDialog` - 35 edges
3. `process_statement()` - 32 edges
4. `xlsx_signature()` - 32 edges
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
- `3. Целевая архитектура` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py
- `Phase 0 — Инвентарь, фикстуры, замеры (первый заход squad)` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py

## Import Cycles
- 2-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/lib.rs`
- 2-file cycle: `crates/tns-core/src/output.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs`
- 2-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/lib.rs`
- 4-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/layout.rs`

## Communities (47 total, 14 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.13
Nodes (9): atomic_json(), _Blob, credentials(), _dpapi(), run_diagnostics(), save_credentials(), stage_database(), validate_database() (+1 more)

### Community 1 - "process.rs"
Cohesion: 0.15
Nodes (16): assert_number(), assert_preview_rows(), cancellation_has_legacy_message(), custom_filename_is_applied(), emit(), fill_rgb(), fixture(), golden() (+8 more)

### Community 2 - "process_statement"
Cohesion: 0.05
Nodes (54): 4. Текущее состояние (факты), Чего ещё нет, 1. Модули, 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), `core_engine.py` (+46 more)

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
Cohesion: 0.06
Nodes (6): calculate_file_sha256(), DatabaseManager, get_app_dir(), ResilientHttpClient, DatabaseViewerDialog, UpdateModalDialog

### Community 7 - "test_parity.py"
Cohesion: 0.05
Nodes (50): 2026-11-17 — Full xlsx signature is now the release gate, 2026-11-17 — Narrow umya xlsx presentation sanitizers, 2026-11-17 — Output writer assumes the statement is sheet 0, 2026-11-17 — Slice 1 gates the workbook through the layout signature, 2026-11-17 — The xlsx signature is the shared parity oracle, 2026-11-17 — umya coalesces equal adjacent column widths, 2026-11-18 — Tauri IPC contract for statement commands, 2026-11-18 — Tauri worktree needs a short target dir and UI dist (+42 more)

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

### Community 12 - "CloudSyncDialog"
Cohesion: 0.08
Nodes (6): 6. Удаляется вместе с Yandex, 7. Данные, S3Config, S3PushEngine, SyncPushWorker, CloudSyncDialog

### Community 13 - "tauri.conf.json"
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

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
Cohesion: 0.09
Nodes (5): CheckUpdatesWorker, DiagnosticService, DiagnosticWorker, DownloadUpdateWorker, SyncPullWorker

### Community 20 - "CheckUpdatesWorker"
Cohesion: 0.13
Nodes (16): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+8 more)

### Community 21 - "DownloadUpdateWorker"
Cohesion: 0.19
Nodes (7): _hash(), install(), wait_pid(), prepare_update(), unpack_release(), grab(), main()

### Community 22 - "SyncPushWorker"
Cohesion: 0.15
Nodes (17): classifies_zones(), classify_zone(), detects_total_rows(), is_word_char(), normalize_header(), normalizes_russian_headers(), numeric_value(), numeric_value_matches_legacy_contract() (+9 more)

### Community 23 - "tns-core"
Cohesion: 0.60
Nodes (5): tns-core, tns-db, tns-excel, tns-parity, tns-studio

### Community 36 - "HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri"
Cohesion: 0.11
Nodes (17): 10. Graphify (карта кода), 11. Первый шаг нового чата, 1. Роль, 2. Что за проект, 3. Зафиксированные решения (не менять без пользователя), 5. Карта репозитория, 6. Что делать дальше (порядок), 7. Жёсткие ограничения (+9 more)

### Community 37 - "output_style.rs"
Cohesion: 0.09
Nodes (18): BORDER_COLOR, COLOR_GREEN, COLOR_RED, conditional_rule(), deviation_formatting(), FILL_CALC_ROW, FILL_DAY, FILL_GREEN (+10 more)

### Community 38 - "process_statement"
Cohesion: 0.23
Nodes (10): TnsError, InvalidNumber, Message, NonFinite, billed_value(), cell(), check_cancel(), is_total_row() (+2 more)

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

### Community 50 - "publish_release.py"
Cohesion: 0.18
Nodes (9): S3Store, sha256(), validate_manifest(), build_if_needed(), main(), release_files(), signature(), constant() (+1 more)

### Community 57 - "default.json"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

## Knowledge Gaps
- **12 isolated node(s):** `Dom`, `Gorod`, `Unknown`, `Day`, `Night` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 319 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_statement()` connect `process_statement` to `ui_sync_components.py`, `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri`, `TNS Energy Studio — полный план миграции на Rust + React + Tauri`, `test_parity.py`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Dom`, `Gorod`, `Unknown` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Why does `DatabaseManager` connect `DatabaseManager` to `sync_manager.py`, `process_statement`, `TNSEnergyStudioWindow`, `CloudSyncDialog`, `DiagnosticService`, `publish_release.py`, `ui_sync_components.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `CloudSyncDialog` (e.g. with `TNSEnergyStudioWindow` and `CheckUpdatesWorker`) actually correct?**
  _`CloudSyncDialog` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.14855072463768115 - nodes in this community are weakly interconnected._