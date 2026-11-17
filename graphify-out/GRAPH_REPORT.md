# Graph Report - tns-review  (2026-11-17)

## Corpus Check
- 67 files · ~61,005 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .ico 2, .css 1)

## Summary
- 809 nodes · 1734 edges · 40 communities (22 shown, 18 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 193 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8b8699c9`
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
- DownloadUpdateWorker
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
- TNS Energy Studio — миграция на Rust + React + Tauri
- TnsError
- StatementKind

## God Nodes (most connected - your core abstractions)
1. `TNSEnergyStudioWindow` - 40 edges
2. `CloudSyncDialog` - 35 edges
3. `process_statement()` - 32 edges
4. `S3Config` - 29 edges
5. `xlsx_signature()` - 28 edges
6. `process_statement()` - 25 edges
7. `DatabaseManager` - 25 edges
8. `SyncError` - 24 edges
9. `main()` - 23 edges
10. `1. Модули` - 22 edges

## Surprising Connections (you probably didn't know these)
- `2026-11-17 — Slice 1 gates the workbook through the layout signature` --references--> `process_statement()`  [INFERRED]
  DECISIONS.md → legacy/pyqt/core_engine.py
- `9. Известные ловушки (проверено на практике)` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `Срез 3 — Tauri commands` --references--> `process_statement()`  [INFERRED]
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

## Communities (40 total, 18 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.05
Nodes (39): atomic_json(), _Blob, CloudDatabaseSync, config_data(), credentials(), database_differs(), _dpapi(), _prefix() (+31 more)

### Community 1 - "process.rs"
Cohesion: 0.14
Nodes (19): assert_number(), assert_preview_rows(), billed_value(), cancellation_has_legacy_message(), cell(), custom_filename_is_applied(), emit(), fixture() (+11 more)

### Community 2 - "process_statement"
Cohesion: 0.06
Nodes (47): 4. Текущее состояние (факты), Чего ещё нет, 1. Модули, 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), 6. Удаляется вместе с Yandex (+39 more)

### Community 3 - "tns-db/src/lib.rs"
Cohesion: 0.06
Nodes (29): backs_up_and_validates(), CalculationRecord, creates_legacy_schema_and_seed(), Database, DbError, Io, Message, Sql (+21 more)

### Community 4 - "TNSEnergyStudioWindow"
Cohesion: 0.06
Nodes (5): main(), TNSEnergyStudioWindow, S3StatusBadge, ToastManager, ToastNotification

### Community 5 - "App.tsx"
Cohesion: 0.07
Nodes (39): dependencies, react@^19.3.1, react-dom@^19.3.1, devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0, typescript@^7.0.2, vite@^8.3.8 (+31 more)

### Community 6 - "DatabaseManager"
Cohesion: 0.09
Nodes (4): calculate_file_sha256(), DatabaseManager, ResilientHttpClient, DatabaseViewerDialog

### Community 7 - "xlsx_signature"
Cohesion: 0.07
Nodes (40): 2026-11-17 — Output writer assumes the statement is sheet 0, 2026-11-17 — Slice 1 gates the workbook through the layout signature, 2026-11-17 — The xlsx signature is the shared parity oracle, 2026-11-17 — umya coalesces equal adjacent column widths, Decisions, _alignment_signature(), _border_signature(), _color_signature() (+32 more)

### Community 9 - "tns-excel/src/lib.rs"
Cohesion: 0.12
Nodes (15): ExcelError, Io, Message, Read, Write, ExcelResult, FALLBACK_WARNING, fixture() (+7 more)

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
Cohesion: 0.12
Nodes (16): 10. Задачи первого захода squad (Phase 0–1), 1. Зафиксированные решения (с заказчиком), 3. Целевая архитектура, 4. Визуальный паритет (критерий приёмки UI), 5. Фазы, 6. Обновления через GitHub (замена Yandex), 8. Риски и fallback, 9. Верификация (gate) (+8 more)

### Community 17 - "gen_fixtures.py"
Cohesion: 0.36
Nodes (6): build_statement(), comma_fmt(), fmt(), main(), rnd(), sha256_file()

### Community 18 - "output.rs"
Cohesion: 0.22
Nodes (18): column_letter(), cell_formula(), cell_number(), cell_text(), HouseStats, open_statement(), set_column_widths(), set_frozen_at_c6() (+10 more)

### Community 20 - "layout.rs"
Cohesion: 0.22
Nodes (12): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+4 more)

### Community 22 - "tns-core/src/lib.rs"
Cohesion: 0.17
Nodes (17): classifies_zones(), classify_zone(), detects_total_rows(), is_word_char(), normalize_header(), normalizes_russian_headers(), numeric_value(), numeric_value_matches_legacy_contract() (+9 more)

### Community 23 - "tns-core"
Cohesion: 0.50
Nodes (5): tns-core, tns-db, tns-excel, tns-parity, tns-studio

### Community 36 - "HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri"
Cohesion: 0.11
Nodes (17): 10. Graphify (карта кода), 11. Первый шаг нового чата, 1. Роль, 2. Что за проект, 3. Зафиксированные решения (не менять без пользователя), 5. Карта репозитория, 6. Что делать дальше (порядок), 7. Жёсткие ограничения (+9 more)

### Community 37 - "TNS Energy Studio — миграция на Rust + React + Tauri"
Cohesion: 0.18
Nodes (10): Handoff и карта кода, Parity-харнесс (legacy — оракул), React UI (Vite), Tauri shell, TNS Energy Studio — миграция на Rust + React + Tauri, Зафиксированные решения, Как запустить legacy-эталон, Полная верификация (+2 more)

### Community 38 - "TnsError"
Cohesion: 0.29
Nodes (5): TnsError, InvalidNumber, Message, NonFinite, check_cancel()

### Community 39 - "StatementKind"
Cohesion: 0.40
Nodes (4): StatementKind, Dom, Gorod, Unknown

## Knowledge Gaps
- **13 isolated node(s):** `Dom`, `Gorod`, `Unknown`, `Day`, `Night` (+8 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 281 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_statement()` connect `process_statement` to `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri`, `TNS Energy Studio — миграция на Rust + React + Tauri`, `xlsx_signature`, `TNS Energy Studio — полный план миграции на Rust + React + Tauri`, `ui_sync_components.py`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Dom`, `Gorod`, `Unknown` to the rest of the system?**
  _13 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05232106815711846 - nodes in this community are weakly interconnected._
- **Why does `DatabaseManager` connect `DatabaseManager` to `sync_manager.py`, `process_statement`, `TNSEnergyStudioWindow`, `S3Config`, `CloudSyncDialog`, `DiagnosticService`, `ui_sync_components.py`, `DownloadUpdateWorker`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `CloudSyncDialog` (e.g. with `TNSEnergyStudioWindow` and `CheckUpdatesWorker`) actually correct?**
  _`CloudSyncDialog` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.13763440860215054 - nodes in this community are weakly interconnected._