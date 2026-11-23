# Graph Report - tns-studio  (2026-11-23)

## Corpus Check
- 85 files · ~102,276 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .ico 2, (none) 1, .css 1)

## Summary
- 1301 nodes · 2792 edges · 79 communities (56 shown, 23 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 258 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c543167e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- sync_manager.py
- process.rs
- process_statement
- tns-db/src/lib.rs
- ExcelError
- package.json
- DatabaseManager
- xlsx_signature
- S3Config
- tns-excel/src/lib.rs
- columns
- compilerOptions
- CloudSyncDialog
- tauri.conf.json
- TNS Energy Studio — полный план миграции на Rust + React + Tauri
- App.tsx
- DiagnosticService
- pdfium.rs
- Статус миграции TNS Energy Studio
- ui_sync_components.py
- tns-core/src/layout.rs
- gen_fixtures.py
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
- tns-pdf/src/layout.rs
- dependencies
- parse.rs
- scripts
- text.rs
- style_statement
- with
- with
- S3Config
- UpdateModalDialog
- PdfError
- AlgorithmHelpDialog
- publish_release.py
- ipc.ts
- TNSEnergyStudioWindow
- S3PushEngine
- Статус миграции TNS Energy Studio
- default.json
- ResilientHttpClient
- update_helper.py
- test_rust_parity.py
- xlsx.rs
- Decisions
- PdfiumError
- Document
- TNS Energy Studio — миграция на Rust + React + Tauri
- tempfile
- PathObject
- TextPage
- json
- TnsError
- TNS Energy Studio 0.2.0
- decode_utf16
- aligned
- vendor/README.md

## God Nodes (most connected - your core abstractions)
1. `Api` - 41 edges
2. `TNSEnergyStudioWindow` - 40 edges
3. `process_statement()` - 36 edges
4. `PdfError` - 35 edges
5. `CloudSyncDialog` - 35 edges
6. `xlsx_signature()` - 34 edges
7. `S3Config` - 29 edges
8. `Statement` - 27 edges
9. `extract_statement()` - 27 edges
10. `process_statement()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `2026-11-17 — Full xlsx signature is now the release gate` --references--> `xlsx_signature()`  [INFERRED]
  DECISIONS.md → tests/parity/parity_lib.py
- `Срез 3 — Tauri commands (готов)` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `Срез 6 — e2e/smoke (готов)` --references--> `process_statement()`  [INFERRED]
  docs/HANDOFF_PROMPT.md → legacy/pyqt/core_engine.py
- `Phase 0 — parity-база` --references--> `xlsx_signature()`  [INFERRED]
  docs/status.md → tests/parity/parity_lib.py
- `PDF input — 7a/7b/7c (CLI и приложение)` --references--> `process_statement()`  [INFERRED]
  docs/status.md → legacy/pyqt/core_engine.py

## Import Cycles
- 2-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/lib.rs`
- 2-file cycle: `crates/tns-core/src/output.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs`
- 2-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/layout.rs`
- 2-file cycle: `crates/tns-pdf/src/lib.rs -> crates/tns-pdf/src/parse.rs -> crates/tns-pdf/src/lib.rs`
- 2-file cycle: `crates/tns-pdf/src/lib.rs -> crates/tns-pdf/src/xlsx.rs -> crates/tns-pdf/src/lib.rs`
- 3-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/layout.rs`
- 3-file cycle: `crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/lib.rs`
- 4-file cycle: `crates/tns-core/src/layout.rs -> crates/tns-core/src/lib.rs -> crates/tns-core/src/process.rs -> crates/tns-core/src/output.rs -> crates/tns-core/src/layout.rs`

## Communities (79 total, 23 thin omitted)

### Community 0 - "sync_manager.py"
Cohesion: 0.13
Nodes (9): atomic_json(), _Blob, credentials(), _dpapi(), run_diagnostics(), save_credentials(), stage_database(), validate_database() (+1 more)

### Community 1 - "process.rs"
Cohesion: 0.13
Nodes (21): assert_number(), assert_preview_rows(), billed_value(), cancellation_has_legacy_message(), cell(), custom_filename_is_applied(), emit(), fill_rgb() (+13 more)

### Community 2 - "process_statement"
Cohesion: 0.18
Nodes (20): 4. Текущее состояние (факты), Чего ещё нет, 1. Модули, Ядро, Phase 1 — скелет, 2. Текущее состояние (эталон), run(), classify_zone() (+12 more)

### Community 3 - "tns-db/src/lib.rs"
Cohesion: 0.10
Nodes (15): backs_up_and_validates(), CalculationRecord, creates_legacy_schema_and_seed(), Database, DbError, Io, Message, Sql (+7 more)

### Community 4 - "ExcelError"
Cohesion: 0.24
Nodes (6): ExcelError, Io, Message, Read, Write, zip_error()

### Community 5 - "package.json"
Cohesion: 0.16
Nodes (15): devDependencies, @types/react@^19.3.0, @types/react-dom@^19.3.0, typescript@^7.0.2, vite@^8.3.8, @vitejs/plugin-react@^6.3.0, name, private (+7 more)

### Community 6 - "DatabaseManager"
Cohesion: 0.13
Nodes (3): calculate_file_sha256(), DatabaseManager, DatabaseViewerDialog

### Community 7 - "xlsx_signature"
Cohesion: 0.14
Nodes (21): _alignment_signature(), _border_signature(), _color_signature(), _conditional_rule_signature(), _data_validation_signature(), _defined_name_signature(), _dxf_signature(), _fill_signature() (+13 more)

### Community 8 - "S3Config"
Cohesion: 0.07
Nodes (34): Args, main(), next_value(), parse_args(), run(), AppState, backup_db(), cancel_statement() (+26 more)

### Community 9 - "tns-excel/src/lib.rs"
Cohesion: 0.12
Nodes (22): default_cell_styles(), ensure_default_cell_styles(), ensures_default_cell_styles_in_written_workbook(), ExcelResult, FALLBACK_WARNING, fixture(), inserts_default_cell_styles_before_cell_xfs_and_dxfs(), mark_inline_string() (+14 more)

### Community 10 - "columns"
Cohesion: 0.11
Nodes (18): columns, billed, coeff, diff, end, main, meter, name (+10 more)

### Community 11 - "compilerOptions"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleResolution, noEmit (+9 more)

### Community 12 - "CloudSyncDialog"
Cohesion: 0.12
Nodes (4): DiagnosticWorker, SyncPullWorker, SyncPushWorker, CloudSyncDialog

### Community 13 - "tauri.conf.json"
Cohesion: 0.08
Nodes (25): app, security, windows, build, beforeBuildCommand, beforeDevCommand, devUrl, frontendDist (+17 more)

### Community 14 - "TNS Energy Studio — полный план миграции на Rust + React + Tauri"
Cohesion: 0.12
Nodes (16): 10. Задачи первого захода squad (Phase 0–1), 1. Зафиксированные решения (с заказчиком), 3. Целевая архитектура, 4. Визуальный паритет (критерий приёмки UI), 5. Фазы, 6. Обновления через GitHub (замена Yandex), 8. Риски и fallback, 9. Верификация (gate) (+8 more)

### Community 15 - "App.tsx"
Cohesion: 0.12
Nodes (27): App(), CalculationPlan, clamp(), describeDetect(), energy(), errorText(), fmt(), HelpTab (+19 more)

### Community 16 - "DiagnosticService"
Cohesion: 0.17
Nodes (9): CloudDatabaseSync, config_data(), database_differs(), _prefix(), PublicHttp, scoped_url(), SyncConflict, SyncError (+1 more)

### Community 17 - "pdfium.rs"
Cohesion: 0.08
Nodes (38): Api, FnClipCountPaths, FnClipCountSegments, FnClipGetPathSegment, FnCloseDocument, FnClosePage, FnDestroyLibrary, FnGetLastError (+30 more)

### Community 18 - "Статус миграции TNS Energy Studio"
Cohesion: 0.23
Nodes (18): column_letter(), cell_formula(), cell_number(), cell_text(), HouseStats, open_statement(), set_column_widths(), set_frozen_at_c6() (+10 more)

### Community 20 - "tns-core/src/layout.rs"
Cohesion: 0.15
Nodes (16): cell(), detect_statement_type(), detects_statement_kinds(), empty_sheet_is_rejected(), extract_metadata(), extract_period(), extracts_metadata(), fixture() (+8 more)

### Community 21 - "gen_fixtures.py"
Cohesion: 0.36
Nodes (6): build_statement(), comma_fmt(), fmt(), main(), rnd(), sha256_file()

### Community 22 - "tns-core/src/lib.rs"
Cohesion: 0.16
Nodes (17): classifies_zones(), classify_zone(), detects_total_rows(), is_word_char(), normalize_header(), normalizes_russian_headers(), numeric_value(), numeric_value_matches_legacy_contract() (+9 more)

### Community 23 - "tns-core"
Cohesion: 0.60
Nodes (6): tns-core, tns-db, tns-excel, tns-parity, tns-pdf, tns-studio

### Community 36 - "HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri"
Cohesion: 0.10
Nodes (19): 10. Graphify (карта кода), 11. Первый шаг нового чата, 1. Роль, 2. Что за проект, 3. Зафиксированные решения (не менять без пользователя), 5. Карта репозитория, 6. Что делать дальше (порядок), 7. Жёсткие ограничения (+11 more)

### Community 37 - "output_style.rs"
Cohesion: 0.08
Nodes (18): BORDER_COLOR, COLOR_GREEN, COLOR_RED, conditional_rule(), deviation_formatting(), FILL_CALC_ROW, FILL_DAY, FILL_GREEN (+10 more)

### Community 38 - "tns-pdf/src/layout.rs"
Cohesion: 0.15
Nodes (21): Band, builds_last_page_bands_with_five_rules(), cluster_asc(), cluster_desc(), clusters_horizontal_rules_top_down(), clusters_vertical_rules_with_tolerance(), COLUMNS, data_bands() (+13 more)

### Community 39 - "dependencies"
Cohesion: 0.22
Nodes (9): dependencies, react@^19.3.1, react-dom@^19.3.1, @tauri-apps/api@^2.12.5, @tauri-apps/plugin-dialog@^2.8.4, react, react-dom, @tauri-apps/api (+1 more)

### Community 40 - "parse.rs"
Cohesion: 0.11
Nodes (35): fallback_boundaries(), fallback_boundaries_extend_number_centers(), Block, CELL_INSET, classifies_total_house_and_meter_rows(), classify_row(), column_boundaries(), continuation() (+27 more)

### Community 41 - "scripts"
Cohesion: 0.40
Nodes (5): scripts, build, dev, preview, typecheck

### Community 42 - "text.rs"
Cohesion: 0.12
Nodes (26): scan_pages(), classifies_zones_like_core(), classify_zone(), detects_sub_rows_and_reserve_meters(), is_minus(), is_reserve(), is_space(), is_sub() (+18 more)

### Community 43 - "style_statement"
Cohesion: 0.25
Nodes (10): apply_box_border(), apply_total_border(), argb(), font(), meter_style(), set_side(), solid_fill(), style_statement() (+2 more)

### Community 44 - "with"
Cohesion: 0.05
Nodes (38): concurrency, cancel-in-progress, group, GITHUB_TOKEN, TAURI_SIGNING_PRIVATE_KEY, TAURI_SIGNING_PRIVATE_KEY_PASSWORD, WINDOWS_CERTIFICATE, WINDOWS_CERTIFICATE_PASSWORD (+30 more)

### Community 45 - "with"
Cohesion: 0.09
Nodes (21): jobs, verify, name, on, pull_request, push, permissions, contents (+13 more)

### Community 47 - "UpdateModalDialog"
Cohesion: 0.12
Nodes (4): DownloadUpdateWorker, get_app_dir(), WindowsUpdateDeployer, UpdateModalDialog

### Community 48 - "PdfError"
Cohesion: 0.13
Nodes (21): PdfError, Invariant, Io, NoStatements, Open, Page, Parse, Pdfium (+13 more)

### Community 49 - "AlgorithmHelpDialog"
Cohesion: 0.11
Nodes (7): Parity-харнесс, UI, БД, Матрица паритета legacy → Rust / React / Tauri, Обновления, AlgorithmHelpDialog, CalculationWorker

### Community 50 - "publish_release.py"
Cohesion: 0.18
Nodes (9): S3Store, sha256(), validate_manifest(), build_if_needed(), main(), release_files(), signature(), constant() (+1 more)

### Community 52 - "ipc.ts"
Cohesion: 0.14
Nodes (13): backupDb(), DetectedFile, excelFilters, HistoryEntry, listenProcessProgress(), Mode, PreviewRow, ProcessPdfArgs (+5 more)

### Community 53 - "TNSEnergyStudioWindow"
Cohesion: 0.06
Nodes (5): main(), TNSEnergyStudioWindow, S3StatusBadge, ToastManager, ToastNotification

### Community 55 - "S3PushEngine"
Cohesion: 0.17
Nodes (10): 2. Контракты ядра, 3. БД (legacy `sync_manager.py:init_db`), 4. Tauri-команды v1 (проект, финализирует `tauri-shell`), 5. UI-токены (QSS `app_gui.py:apply_theme`), 6. Удаляется вместе с Yandex, `core_engine.py`, `tns_input.py`, Инвентарь legacy/pyqt и контракты для миграции (+2 more)

### Community 56 - "Статус миграции TNS Energy Studio"
Cohesion: 0.20
Nodes (9): PDF input — 7a/7b/7c (CLI и приложение), Phase 0 — parity-база, Phase 2 — release 0.2.0 (опубликован как `v0.2.0-1`), В работе, Известные девиации, Проверки, Сделано, Следующие шаги (+1 more)

### Community 57 - "default.json"
Cohesion: 0.33
Nodes (5): description, identifier, permissions, $schema, windows

### Community 59 - "update_helper.py"
Cohesion: 0.20
Nodes (7): _hash(), install(), wait_pid(), prepare_update(), unpack_release(), grab(), main()

### Community 60 - "test_rust_parity.py"
Cohesion: 0.33
Nodes (7): 2026-11-17 — The xlsx signature is the shared parity oracle, diff_dicts(), _run_rust(), _rust_command(), test_rust_result_matches_golden(), test_rust_xlsx_layout_matches_golden(), test_rust_xlsx_matches_golden()

### Community 61 - "xlsx.rs"
Cohesion: 0.15
Nodes (34): Balance, House, Layout, Meter, Official, PageInfo, Source, Statement (+26 more)

### Community 62 - "Decisions"
Cohesion: 0.11
Nodes (18): 2026-11-17 — Full xlsx signature is now the release gate, 2026-11-17 — Narrow umya xlsx presentation sanitizers, 2026-11-17 — Output writer assumes the statement is sheet 0, 2026-11-17 — Slice 1 gates the workbook through the layout signature, 2026-11-17 — umya coalesces equal adjacent column widths, 2026-11-18 — Build the UI before Tauri checks in CI, 2026-11-18 — Release 0.2.0 builds in the workspace target, 2026-11-18 — Tauri IPC contract for statement commands (+10 more)

### Community 63 - "PdfiumError"
Cohesion: 0.17
Nodes (10): api(), API, bind(), candidates(), library_name(), load(), loads_vendored_pdfium(), PdfiumError (+2 more)

### Community 64 - "Document"
Cohesion: 0.20
Nodes (6): Document, FpdfDocument, FpdfPage, last_error(), last_error_name(), Page

### Community 65 - "TNS Energy Studio — миграция на Rust + React + Tauri"
Cohesion: 0.18
Nodes (10): Handoff и карта кода, Legacy-эталон, Parity-харнесс, TNS Energy Studio — миграция на Rust + React + Tauri, Updater и GitHub Releases, Быстрый старт, Ветки, Зафиксированные решения (+2 more)

### Community 66 - "tempfile"
Cohesion: 0.20
Nodes (9): normalize_result(), run_oracle(), sha256_file(), main(), test_fixtures_exist(), test_golden_manifest_hashes(), test_golden_reproducible(), test_numeric_value() (+1 more)

### Community 67 - "PathObject"
Cohesion: 0.22
Nodes (6): FPDF_PAGEOBJ_PATH, FPDF_SEGMENT_LINETO, LibraryVersion, PathObject, Rect, Segment

### Community 68 - "TextPage"
Cohesion: 0.39
Nodes (3): decode_char(), FpdfTextPage, TextPage

### Community 69 - "json"
Cohesion: 0.36
Nodes (4): fixtures_manifest(), golden_manifest(), parity_dirs(), ParityDirs

### Community 70 - "TnsError"
Cohesion: 0.29
Nodes (5): TnsError, InvalidNumber, Message, NonFinite, check_cancel()

### Community 71 - "TNS Energy Studio 0.2.0"
Cohesion: 0.40
Nodes (4): TNS Energy Studio 0.2.0, Ограничения, Установка, Что внутри

### Community 72 - "decode_utf16"
Cohesion: 0.40
Nodes (3): decode_utf16(), decode_utf16_bytes(), decodes_surrogate_pairs()

## Knowledge Gaps
- **24 isolated node(s):** `Pdfium`, `Open`, `Page`, `Parse`, `Invariant` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 427 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_statement()` connect `Decisions` to `TNS Energy Studio — миграция на Rust + React + Tauri`, `process_statement`, `tempfile`, `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri`, `TNS Energy Studio 0.2.0`, `TNS Energy Studio — полный план миграции на Rust + React + Tauri`, `AlgorithmHelpDialog`, `ui_sync_components.py`, `S3PushEngine`, `Статус миграции TNS Energy Studio`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `TNSEnergyStudioWindow` (e.g. with `1. Модули` and `2. Текущее состояние (эталон)`) actually correct?**
  _`TNSEnergyStudioWindow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Pdfium`, `Open`, `Page` to the rest of the system?**
  _24 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `sync_manager.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Why does `9. Известные ловушки (проверено на практике)` connect `HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri` to `ipc.ts`, `Decisions`, `xlsx_signature`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `process_statement()` (e.g. with `2026-11-17 — Narrow umya xlsx presentation sanitizers` and `2026-11-17 — Slice 1 gates the workbook through the layout signature`) actually correct?**
  _`process_statement()` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Should `process.rs` be split into smaller, more focused modules?**
  _Cohesion score 0.1265597147950089 - nodes in this community are weakly interconnected._