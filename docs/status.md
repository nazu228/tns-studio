# Статус миграции TNS Energy Studio

Обновлено: 2026-11-23. Ветка: `parity-harness` (релиз 0.2.0 опубликован как `v0.2.0-1`; PDF 7a–7c готовы).

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
  `apps/ui/dist`, 10 команд. `detect_statement` читает файл/папку (`.xlsx`/`.pdf`)
  и отдаёт кандидатов; `process_statement` идёт через `spawn_blocking`, progress
  `process-progress`, `cancel_statement`, запись истории/домов в SQLite;
  `process_pdf` парсит PDF и пишет стандартные ведомости с тем же прогрессом;
  `cargo test` — **9 passed, 1 ignored** (real-PDF), `cargo check` ok (Tauri 2.12).
- [x] Tauri dialog plugin + capabilities (`core:default`, `dialog:default`) для UI среза 4.
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
- [x] UI invoke, срез 4: `apps/ui/src/ipc.ts` — типизированный мост; detect файла/папки,
  process both/dom/gorod, прогресс 5–45/50–95, отмена, история/бэкап/open; моки и
  `setTimeout` удалены, дизайн сохранён. `npm ci`, typecheck, build — ok;
  `scripts/verify.ps1 -RequireRustOutput` — All checks passed.
- [x] Updater/CI, срез 5: `tauri-plugin-updater`, endpoint GitHub `latest.json`,
  `createUpdaterArtifacts`, capability `updater:default`, реальный `update_check`;
  `.github/workflows/ci.yml` и `release.yml` (Windows, verify, NSIS, updater zip,
  `latest.json`, optional Authenticode), `scripts/release-latest-json.ps1`,
  README с секретами. `verify.ps1` теперь собирает UI до `cargo check src-tauri`
  и запускает `cargo test src-tauri`.
- [x] E2E/smoke, срез 6: live Tauri + WebView2 CDP. UI загрузился, `detect_statement`
  и `process_statement` прошли через реальный IPC, результаты/метрики/баланс,
  история и бэкап БД проверены. Native file dialog открывается, но его выбор
  автоматизировать не удалось: UI-путь расчёта проверен инъекцией source/detect
  в React state. Live-отмена не поймана — fixture слишком быстрый.

### Phase 2 — release 0.2.0 (опубликован как `v0.2.0-1`)
- [x] Версия `0.2.0` в `tauri.conf.json`, `src-tauri/Cargo.toml`, UI package и
  subtitle; `Cargo.lock` обновлён.
- [x] Release workflow исправлен под workspace: артефакты в
  `target/release/bundle/nsis`, `RELEASE_NOTES.md` в тело GitHub Release и
  `latest.json`; `beforeBuildCommand`/`beforeDevCommand` — `npm run build`/
  `npm run dev` (Tauri запускает их из `apps/ui`).
- [x] `RELEASE_NOTES.md` и release checklist в README.
- [x] Локальная unsigned NSIS-сборка:
  `target/release/bundle/nsis/TNS Energy Studio_0.2.0_x64-setup.exe`
  (5 477 889 байт, SHA256 `6130A50DAC575DA9C9E90299EB637675F905DEB4BEE2058E8D95351F12A70686`).
  Release binary CDP smoke: UI загрузился, title и `v0.2.0` видны.
- [x] Подписанные updater-артефакты: ключ создан пользователем, `pubkey` установлен
  (`8f9ab17`), secrets добавлены; release workflow собрал `*-setup.exe` и `.exe.sig`.
- [x] GitHub Release `v0.2.0-1` опубликован: installer, `.exe.sig`, `latest.json`;
  `releases/latest/download/latest.json` отдаёт версию 0.2.0 и URL на installer.
  Старый тег `v0.2.0` остался без релиза и не используется.

### PDF input — 7a/7b/7c (CLI и приложение)
- [x] `crates/tns-pdf`: PDFium 153.0.7999.0, векторная сетка, детекция ведомостей,
  27 колонок, дома/ПУ, жёсткие инварианты; городской PDF 82 стр. — 22 дома,
  `736 051,312` / `4 309 766,80`, 918 ПУ. Корректировки распознают базовый период.
- [x] 26 unit-тестов + CLI `parse <pdf> --json <dir> [--xlsx <dir>]`; JSON
  schema_version=1; реальный PDF — через ignored-тест/CLI, PDF/JSON не коммитятся.
- [x] 7b: `Statement` проецируется на исходный layout 1C и проходит через
  `tns_core::process_statement` — стандартные `Сводка по домам` + `Ведомость ЭП`.
  Имена `<contract>_<Month>_<Year>[_за_<BaseMonth>_<BaseYear>].xlsx`, дубликаты
  получают `_2`. Все 5 пользовательских PDF дают корректные итоги:
  736 051,312 / 1 032 745,77 / 137 107,602 / 223 073,372; openpyxl без warning.
- [x] 7c: Tauri `process_pdf` + UI. `detect_statement` видит `.pdf` (kind `pdf`,
  без парсинга при выборе); расчёт из UI парсит PDF, фильтрует по режиму
  both/dom/gorod, пишет все ведомости и показывает прогресс/итоги. Live-smoke
  через WebView2 CDP: dom PDF — 3 дома, `137 107,602`; combined 226-стр. PDF —
  две ведомости (`736 051,312` и `1 032 745,77`), обе записи в истории,
  выходные xlsx проверены openpyxl. PDFium DLL бандлится как Tauri resource,
  dev/test fallback — `crates/tns-pdf/vendor`.

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
| `cargo check --manifest-path src-tauri/Cargo.toml` | ok (Tauri 2.12, dialog+updater+pdfium resource) |
| `cargo test --manifest-path src-tauri/Cargo.toml` | 9 passed, 1 ignored (real PDF) |
| `cargo test --manifest-path crates/tns-excel/Cargo.toml` | 7 passed |
| `cargo test -p tns-pdf` | 26 passed, 2 ignored |
| `cargo build --manifest-path crates/tns-parity/Cargo.toml` | ok |
| `.\scripts\verify.ps1 -RequireRustOutput` | All checks passed |
| `scripts/release-latest-json.ps1` | проверен на dummy installer `.exe`/`.sig` |
| `.github/workflows/release.yml` | run 44471114550 success: verify, NSIS, `.exe.sig`, `latest.json`, GitHub Release |
| live Tauri smoke (WebView2 CDP) | UI loaded; detect/process/results/history/backup ok |
| release build (unsigned NSIS) | `TNS Energy Studio_0.2.0_x64-setup.exe`, CDP smoke ok |
| `npm --prefix apps/ui ci` | ok (26 packages, lock sync) |
| `git diff parity-harness -- legacy/pyqt tests/parity/fixtures` | пусто |

## В работе

- Ручной smoke native file dialog, live-отмены и `open_file`/`open_folder` на
  release-сборке; дальнейшие релизы — обычным тегом `v*`.

## Известные девиации

- Облачная синхронизация и Yandex удалены по решению; UI не содержит кнопку «Облако».
- React UI работает через реальный Tauri IPC. Live-smoke 2026-11-18 проверен через
  WebView2 CDP: detect/process/results/history/backup; native file dialog открывается,
  но выбор файла и live-отмена автоматизированы не были. `open_file`/`open_folder`
  не запускались (открывают Explorer).
- Скриншоты legacy сняты на Windows-платформе (Segoe UI, кириллица); на другой машине
  пиксельный diff может отличаться — сравнивать с эталоном этой машины.
- Writer рассчитан на один исходный лист. Legacy берёт `wb.active`, Rust пока
  `book.sheet(0)`; порядок сводки для extra-листов исправлен, но active-sheet
  multi-sheet вход требует отдельного фикса и теста.
- `tns-excel` делает узкий post-processing xlsx: удаляет пустой `<diagonal/>`
  только у границ со стилем и ставит `t="inlineStr"` пустой ячейке A итоговой
  строки сводки. Это компенсация ограничений umya, не ослабление oracle.
- `detect_statement` папки возвращает `files` и агрегирует `kind` только при
  единогласии типов; mixed/unknown UI разбирает по `files`.
- `process_statement` при ошибке SQLite возвращает уже сохранённый результат с
  `history_warning`, не Err.
- Tauri IPC: аргументы в JS camelCase (`sourcePath`, `outputDir`, `customFilename`);
  событие прогресса — `process-progress` с `{percent, message}`.
- Updater `pubkey` установлен (`8f9ab17`), secrets добавлены, release workflow
  успешно собрал `*-setup.exe` + `.exe.sig`; GitHub Release `v0.2.0-1` опубликован.
- GitHub CDN для `releases/latest/download/latest.json` может отдавать старую
  версию несколько минут после замены asset; проверять с cache-buster или после
  истечения кеша. URL installer в `latest.json` использует точки вместо пробелов,
  как GitHub переименовывает assets.
- Authenticode-шаг опционален и подписывает `.exe` после Tauri bundling; это
  инвалидирует `.exe.sig`. Для полной цепочки нужен `bundle.windows.signCommand`
  до updater-подписи; без сертификата шаг пропускается.
- PDF-парсер 7a–7c работает только с iText-ведомостями, у которых есть векторная
  сетка. Текстовый разбор без сетки даёт 20 домов вместо 22; сканы без текстового
  слоя отклоняются. PDFium DLL 153.0.7999.0 вендорен (~7,26 МБ) и бандлится как
  Tauri resource; CLI и приложение (`process_pdf`) пишут стандартный xlsx.
  PDFium API не потокобезопасен: парсить документы последовательно.
- В PDF нет отдельной зоны ОДН; пустая зона в текущей модели попадает в `odn`
  (как в Excel-модели), поэтому прототип с `single` и текущий JSON расходятся
  только по имени зоны, не по суммам.
- PDFium может отдавать управляющие символы (например STX в названиях улиц);
  `tns-pdf` вырезает их перед записью в xlsx, иначе XML повреждается. Синтетический
  source-проекция получает дефолтный `Normal` style через
  `tns-excel::ensure_default_cell_styles`, иначе openpyxl/Excel видят файл
  повреждённым.

## Следующие шаги

1. Ручной smoke native file dialog, live-отмены и `open_file`/`open_folder` на release-сборке.
2. Проверить обновление с предыдущей версии через `latest.json`.
3. Финальный critic и визуальная приёмка на release-сборке.
4. При желании удалить старый тег `v0.2.0` вручную; агент не может удалять теги.
