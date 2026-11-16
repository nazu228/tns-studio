# Graph Report - tns-studio  (2026-11-16)

## Corpus Check
- 60 files · ~54,963 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .ico 2, (none) 1, .css 1)

## Summary
- 719 nodes · 1511 edges · 36 communities (17 shown, 19 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 168 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `70c07265`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sync_manager.py
- process.rs
- core_engine.py
- tns-db/src/lib.rs
- TNSEnergyStudioWindow
- App.tsx
- DatabaseManager
- test_parity.py
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
- Статус миграции TNS Energy Studio
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

## God Nodes (most connected - your core abstractions)
1. `TNSEnergyStudioWindow` - 40 edges
2. `CloudSyncDialog` - 35 edges
3. `S3Config` - 29 edges
4. `process_statement()` - 25 edges
5. `DatabaseManager` - 25 edges
6. `SyncError` - 24 edges
7. `main()` - 23 edges
8. `1. Модули` - 22 edges
9. `process_statement()` - 21 edges
10. `CloudDatabaseSync` - 21 edges

## Surprising Connections (you probably didn't know these)
- `4. Tauri-команды v1 (проект, финализирует `tauri-shell`)` --references--> `process_statement()`  [INFERRED]
  docs/inventory.md → legacy/pyqt/core_engine.py
- `3. Целевая архитектура` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py
- `Phase 0 — Инвентарь, фикстуры, замеры (первый заход squad)` --references--> `process_statement()`  [INFERRED]
  docs/TNS_MIGRATION_PLAN.md → legacy/pyqt/core_engine.py
- ``tns_input.py`` --references--> `normalize_header()`  [INFERRED]
  docs/inventory.md → legacy/pyqt/tns_input.py
- `1. Модули` --references--> `TNSEnergyStudioWindow`  [INFERRED]
  docs/inventory.md → legacy/pyqt/app_gui.py

## Import Cycles
- 2-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/lib.rs`
- 2-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/layout.rs`

## Communities (36 total, 19 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.06
Nodes (34): atomic_json(), _Blob, CloudDatabaseSync, config_data(), credentials(), database_differs(), _dpapi(), _prefix() (+26 more)

### Community 1 - "process.rs"
Cohesion: 0.05
Nodes (58): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+50 more)

### Community 2 - "core_engine.py"
Cohesion: 0.07
Nodes (37): 1. Модули, Parity-харнесс, UI, БД, Матрица паритета legacy → Rust / React / Tauri, Обновления, Ядро, Phase 1 — скелет (+29 more)

### Community 3 - "tns-db/src/lib.rs"
Cohesion: 0.07
Nodes (24): backs_up_and_validates(), CalculationRecord, creates_legacy_schema_and_seed(), Database, DbError, Io, Message, Sql (+16 more)

### Community 4 - "TNSEnergyStudioWindow"
Cohesion: 0.07
Nodes (5): main(), TNSEnergyStudioWindow, S3StatusBadge, ToastManager, ToastNotification

### Community 5 - "App.tsx"
Cohesion: 0.07
Nodes (39): dependencies, react@^19.3.1, react-dom@^19.3.1, devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0, typescript@^7.0.2, vite@^8.3.8 (+31 more)

### Community 6 - "DatabaseManager"
Cohesion: 0.09
Nodes (4): calculate_file_sha256(), DatabaseManager, ResilientHttpClient, DatabaseViewerDialog

### Community 7 - "test_parity.py"
Cohesion: 0.11
Nodes (15): fixtures_manifest(), golden_manifest(), parity_dirs(), ParityDirs, diff_dicts(), normalize_result(), run_oracle(), sha256_file() (+7 more)

### Community 8 - "S3Config"
Cohesion: 0.10
Nodes (11): 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), 6. Удаляется вместе с Yandex, `core_engine.py`, `tns_input.py`, Инвентарь legacy/pyqt и контракты для миграции (+3 more)

### Community 9 - "tns-excel/src/lib.rs"
Cohesion: 0.14
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

### Community 18 - "Статус миграции TNS Energy Studio"
Cohesion: 0.25
Nodes (7): Phase 0 — parity-база, В работе, Известные девиации, Проверки, Сделано, Следующие шаги, Статус миграции TNS Energy Studio

### Community 23 - "tns-core"
Cohesion: 0.67
Nodes (4): tns-core, tns-db, tns-excel, tns-studio

## Knowledge Gaps
- **12 isolated node(s):** `Dom`, `Gorod`, `Unknown`, `Day`, `Night` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 256 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatabaseManager` connect `DatabaseManager` to `sync_manager.py`, `core_engine.py`, `TNSEnergyStudioWindow`, `S3Config`, `CloudSyncDialog`, `DiagnosticService`, `ui_sync_components.py`, `DownloadUpdateWorker`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Dom`, `Gorod`, `Unknown` to the rest of the system?**
  _12 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.059794214715589204 - nodes in this community are weakly interconnected._
- **Why does `TNSEnergyStudioWindow` connect `TNSEnergyStudioWindow` to `core_engine.py`, `DatabaseManager`, `S3Config`, `CloudSyncDialog`, `UpdateModalDialog`, `ui_sync_components.py`, `CheckUpdatesWorker`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `CloudSyncDialog` (e.g. with `TNSEnergyStudioWindow` and `CheckUpdatesWorker`) actually correct?**
  _`CloudSyncDialog` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.050200803212851405 - nodes in this community are weakly interconnected._