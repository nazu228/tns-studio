# Graph Report - review2  (2026-11-17)

## Corpus Check
- 68 files · ~63,516 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .ico 2, .css 1)

## Summary
- 877 nodes · 1898 edges · 50 communities (24 shown, 26 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 201 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `de584b9f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sync_manager.py
- process.rs
- process_statement
- tns-db/src/lib.rs
- TNSEnergyStudioWindow
- App.tsx
- DatabaseManager
- xlsx_signature
- S3Config
- tns-excel/src/lib.rs
- columns
- compilerOptions
- CloudSyncDialog
- tauri.conf.json
- TNS Energy Studio — полный план миграции на Rust + React + Tauri
- UpdateModalDialog
- DiagnosticService
- gen_fixtures.py
- output.rs
- ui_sync_components.py
- layout.rs
- SyncPushWorker
- tns-core/src/lib.rs
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
- StatementKind
- style_statement
- ToastManager
- ExcelError
- Матрица паритета legacy → Rust / React / Tauri
- CheckUpdatesWorker
- S3StatusBadge
- ToastNotification
- AlgorithmHelpDialog
- aligned

## God Nodes (most connected - your core abstractions)
1. `TNSEnergyStudioWindow` - 40 edges
2. `CloudSyncDialog` - 35 edges
3. `process_statement()` - 33 edges
4. `xlsx_signature()` - 32 edges
5. `S3Config` - 29 edges
6. `process_statement()` - 26 edges
7. `DatabaseManager` - 25 edges
8. `SyncError` - 24 edges
9. `main()` - 23 edges
10. `TnsError` - 22 edges

## Surprising Connections (you probably didn't know these)
- `2026-11-17 — Slice 1 gates the workbook through the layout signature` --references--> `process_statement()`  [INFERRED]
  DECISIONS.md → legacy/pyqt/core_engine.py
- `Срез 3 — Tauri commands` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `Phase 0 — parity-база` --references--> `xlsx_signature()`  [INFERRED]
  docs/status.md → tests/parity/parity_lib.py
- `3. Целевая архитектура` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py
- `Phase 0 — Инвентарь, фикстуры, замеры (первый заход squad)` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py

## Import Cycles
- 2-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/lib.rs`
- 2-file cycle: `crates/tns-core/src/output.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs`
- 2-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/lib.rs`
- 3-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/layout.rs`
- 4-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/layout.rs`

## Communities (50 total, 26 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.05
Nodes (40): atomic_json(), _Blob, CloudDatabaseSync, config_data(), credentials(), database_differs(), _dpapi(), _prefix() (+32 more)

### Community 1 - "process.rs"
Cohesion: 0.12
Nodes (21): assert_number(), assert_preview_rows(), billed_value(), cancellation_has_legacy_message(), cell(), custom_filename_is_applied(), emit(), fill_rgb() (+13 more)

### Community 2 - "process_statement"
Cohesion: 0.07
Nodes (48): 4. Текущее состояние (факты), Чего ещё нет, 1. Модули, 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), 6. Удаляется вместе с Yandex (+40 more)

### Community 3 - "tns-db/src/lib.rs"
Cohesion: 0.05
Nodes (29): backs_up_and_validates(), CalculationRecord, creates_legacy_schema_and_seed(), Database, DbError, Io, Message, Sql (+21 more)

### Community 5 - "App.tsx"
Cohesion: 0.07
Nodes (39): dependencies, react@^19.3.1, react-dom@^19.3.1, devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0, typescript@^7.0.2, vite@^8.3.8 (+31 more)

### Community 7 - "xlsx_signature"
Cohesion: 0.07
Nodes (42): 2026-11-17 — Full xlsx signature is now the release gate, 2026-11-17 — Narrow umya xlsx presentation sanitizers, 2026-11-17 — Output writer assumes the statement is sheet 0, 2026-11-17 — Slice 1 gates the workbook through the layout signature, 2026-11-17 — The xlsx signature is the shared parity oracle, 2026-11-17 — umya coalesces equal adjacent column widths, Decisions, _alignment_signature() (+34 more)

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
Cohesion: 0.11
Nodes (17): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+9 more)

### Community 14 - "TNS Energy Studio — полный план миграции на Rust + React + Tauri"
Cohesion: 0.07
Nodes (19): 10. Задачи первого захода squad (Phase 0–1), 1. Зафиксированные решения (с заказчиком), 3. Целевая архитектура, 4. Визуальный паритет (критерий приёмки UI), 5. Фазы, 6. Обновления через GitHub (замена Yandex), 7. Данные, 8. Риски и fallback (+11 more)

### Community 17 - "gen_fixtures.py"
Cohesion: 0.36
Nodes (6): build_statement(), comma_fmt(), fmt(), main(), rnd(), sha256_file()

### Community 18 - "output.rs"
Cohesion: 0.23
Nodes (18): column_letter(), cell_formula(), cell_number(), cell_text(), HouseStats, open_statement(), set_column_widths(), set_frozen_at_c6() (+10 more)

### Community 20 - "layout.rs"
Cohesion: 0.22
Nodes (12): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+4 more)

### Community 21 - "SyncPushWorker"
Cohesion: 0.18
Nodes (3): DownloadUpdateWorker, SyncPullWorker, SyncPushWorker

### Community 22 - "tns-core/src/lib.rs"
Cohesion: 0.16
Nodes (17): classifies_zones(), classify_zone(), detects_total_rows(), is_word_char(), normalize_header(), normalizes_russian_headers(), numeric_value(), numeric_value_matches_legacy_contract() (+9 more)

### Community 23 - "tns-core"
Cohesion: 0.50
Nodes (5): tns-core, tns-db, tns-excel, tns-parity, tns-studio

### Community 36 - "HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri"
Cohesion: 0.11
Nodes (17): 10. Graphify (карта кода), 11. Первый шаг нового чата, 1. Роль, 2. Что за проект, 3. Зафиксированные решения (не менять без пользователя), 5. Карта репозитория, 6. Что делать дальше (порядок), 7. Жёсткие ограничения (+9 more)

### Community 37 - "output_style.rs"
Cohesion: 0.10
Nodes (18): BORDER_COLOR, COLOR_GREEN, COLOR_RED, conditional_rule(), deviation_formatting(), FILL_CALC_ROW, FILL_DAY, FILL_GREEN (+10 more)

### Community 38 - "TnsError"
Cohesion: 0.29
Nodes (5): TnsError, InvalidNumber, Message, NonFinite, check_cancel()

### Community 39 - "StatementKind"
Cohesion: 0.40
Nodes (4): StatementKind, Dom, Gorod, Unknown

### Community 40 - "style_statement"
Cohesion: 0.25
Nodes (10): apply_box_border(), apply_total_border(), argb(), font(), meter_style(), set_side(), solid_fill(), style_statement() (+2 more)

### Community 42 - "ExcelError"
Cohesion: 0.24
Nodes (6): ExcelError, Io, Message, Read, Write, zip_error()

### Community 43 - "Матрица паритета legacy → Rust / React / Tauri"
Cohesion: 0.20
Nodes (6): Parity-харнесс, UI, БД, Матрица паритета legacy → Rust / React / Tauri, Обновления, CalculationWorker

## Knowledge Gaps
- **13 isolated node(s):** `Day`, `Night`, `Odn`, `InvalidNumber`, `NonFinite` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 300 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_statement()` connect `process_statement` to `ui_sync_components.py`, `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri`, `TNS Energy Studio — полный план миграции на Rust + React + Tauri`, `xlsx_signature`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Day`, `Night`, `Odn` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05156369183829138 - nodes in this community are weakly interconnected._
- **Why does `DatabaseManager` connect `DatabaseManager` to `sync_manager.py`, `process_statement`, `TNSEnergyStudioWindow`, `S3Config`, `CloudSyncDialog`, `DiagnosticService`, `ui_sync_components.py`, `SyncPushWorker`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `CloudSyncDialog` (e.g. with `TNSEnergyStudioWindow` and `CheckUpdatesWorker`) actually correct?**
  _`CloudSyncDialog` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.12100840336134454 - nodes in this community are weakly interconnected._