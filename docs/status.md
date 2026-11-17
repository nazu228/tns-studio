# Статус миграции TNS Energy Studio

Обновлено: 2026-11-17. Ветка: `parity-harness` (срез 2 output workbook).

## Сделано

### Phase 0 — parity-база
- [x] Снапшот legacy PySide6 в `legacy/pyqt/` (не изменяется).
- [x] План миграции `docs/TNS_MIGRATION_PLAN.md`.
- [x] `docs/inventory.md` — модули, контракты, схема БД, токены.
- [x] `docs/parity-matrix.md` — матрица паритета.
- [x] `tests/parity/`:
  - 3 фикстуры: `dom_april_2026.xlsx`, `gorod_april_2026.xlsx`, `dom_march_2026.xlsx`;
  - golden-выходы legacy (xlsx + JSON) и манифест;
  - 5 скриншотов legacy: пустое окно, справка, результаты dom/gorod, ошибка;
  - независимая `xlsx_signature`: полный сигнал (порядок листов, стили, CF,
    hyperlinks, hidden rows/cols, defined names, validations) и layout-режим
    `include_styles=False` для среза writer'а;
  - `crates/tns-parity` — драйвер Rust-результата для pytest;
  - pytest-харнесс: **22 passed, 0 xfailed** (полный xlsx-сигнал enforced;
    layout-паритет на 3 фикстурах).

### Phase 1 — скелет
- [x] `apps/ui` — Vite + React + TS, главное окно TNS (design parity):
  шапка, режимы, источник, месяц/год, карточки, вкладки, таблица, итоги, справка.
  Кнопка «Облако» и S3-бейдж удалены. `npm run typecheck` и `npm run build` проходят.
- [x] `crates/tns-core` — Rust-порт чистых функций:
  `normalize_header`, `row_type`, `safe_float`, `numeric_value`, `classify_zone`, `total_row`.
  `cargo check` и `cargo test` проходят: **6 passed**.
- [x] MSVC Build Tools + Windows SDK установлены; `scripts/cargo.ps1` запускает cargo в их окружении.
- [x] `crates/tns-db` — локальная SQLite: схема legacy, seed организаций/тарифов,
  история расчётов, upsert домов, локальный бэкап, валидация. **4 passed**.
- [x] `src-tauri` — Tauri 2 shell: окно 1280×880, иконка, `frontendDist` на
  `apps/ui/dist`, команды `history_list`, `backup_db`, `open_file`, `open_folder`,
  `config_get`, `detect_statement`, `process_statement`, `update_check`.
  `cargo check` проходит (Tauri 2.12).
- [x] `crates/tns-excel` — обёртка над `umya-spreadsheet` 3.1.1 (MIT):
  чтение/запись существующей книги, `safe_save` с атомарной заменой и
  fallback-копией; узкие post-processors для пустого `<diagonal/>` и пустой
  inlineStr-ячейки. **5 passed**.
- [x] `tns-core`: `resolve_layout`, `extract_metadata`, `detect_statement_type`
  портированы и проверены на dom/gorod фикстурах; **10 passed**.
- [x] `process_statement` — парсинг домов/ПУ/субабонентов, валидация billed values,
  period/paths/имена, итоги, `preview_rows`, `balance`, прогресс 5/15/35/65/90/100,
  отмена. Result совпадает с golden на dom/gorod; **16 passed**.
- [x] Выходная книга, срез 1: лист «Ведомость ЭП» (значения, формулы SUM/ROUND/IF,
  субабоненты), лист «Сводка по домам» первым, merge A1:J1/A2:J2/A3:J3, freeze C6,
  ширины/высоты, `safe_save`, фактический `target_path`/`warning`. Layout-паритет
  с golden на всех 3 фикстурах.
- [x] Выходная книга, срез 2: стили Segoe UI, заливки, границы, number formats,
  CF `H6:Hn`, hyperlink B6/B7; полный `xlsx_signature` — **0 diffs** на всех 3
  фикстурах, pytest **22 passed / 0 xfailed**.
- [ ] Tauri `detect_statement`/`process_statement`, UI invoke, updater/CI.
- [ ] Интеграция React UI с Tauri invoke, updater, CI.

## Проверки

| Проверка | Результат |
|---|---|
| `python -m pytest tests/parity -q` | 22 passed, 0 xfailed |
| `$env:TNS_REQUIRE_RUST_OUTPUT='1'; python -m pytest tests/parity -q` | 22 passed |
| `cd apps/ui && npm run typecheck` | ok |
| `cd apps/ui && npm run build` | ok (dist) |
| `cargo check --manifest-path crates/tns-core/Cargo.toml` | ok |
| `cargo test --manifest-path crates/tns-core/Cargo.toml` | 16 passed |
| `cargo test --manifest-path crates/tns-db/Cargo.toml` | 4 passed |
| `cargo check --manifest-path src-tauri/Cargo.toml` | ok (Tauri 2.12) |
| `cargo test --manifest-path crates/tns-excel/Cargo.toml` | 5 passed |
| `cargo build --manifest-path crates/tns-parity/Cargo.toml` | ok |
| `git diff parity-harness -- legacy/pyqt tests/parity/fixtures` | пусто |

## В работе

- Tauri commands: реальные `detect_statement`/`process_statement`, прогресс/отмена, запись в БД.

## Известные девиации

- Облачная синхронизация и Yandex удалены по решению; UI не содержит кнопку «Облако».
- React UI пока на моковых данных; реальные данные появятся после Tauri-команд.
- Скриншоты legacy сняты на Windows-платформе (Segoe UI, кириллица); на другой машине
  пиксельный diff может отличаться — сравнивать с эталоном этой машины.
- Writer рассчитан на один исходный лист. Legacy берёт `wb.active`, Rust пока
  `book.sheet(0)`; порядок сводки для extra-листов исправлен, но active-sheet
  multi-sheet вход требует отдельного фикса и теста.
- `tns-excel` делает узкий post-processing xlsx: удаляет пустой `<diagonal/>`
  только у границ со стилем и ставит `t="inlineStr"` пустой ячейке A итоговой
  строки сводки. Это компенсация ограничений umya, не ослабление oracle.

## Следующие шаги

1. `src-tauri`: реальные `detect_statement`/`process_statement`, прогресс/отмена, запись в БД.
2. UI invoke/listen вместо мока; прогресс/ошибка/отмена/история; дизайн не менять.
3. Updater/CI: GitHub Releases + `latest.json` + minisign/Authenticode.
4. Critic + полный `scripts/verify.ps1 -RequireRustOutput`.
5. `graphify update .` после изменений кода (срез 2 уже обновлён).
