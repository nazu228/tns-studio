# Статус миграции TNS Energy Studio

Обновлено: 2026-11-18. Ветка: `parity-harness` (подготовка релиза 0.2.0).

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
  `apps/ui/dist`, 9 команд. `detect_statement` читает файл/папку и отдаёт
  кандидатов; `process_statement` идёт через `spawn_blocking`, progress
  `process-progress`, `cancel_statement`, запись истории/домов в SQLite;
  `cargo test` — **7 passed**, `cargo check` ok (Tauri 2.12).
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

### Phase 2 — release 0.2.0 (подготовка)
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
- [ ] Подписанные updater-артефакты: локальная генерация `.key` заблокирована
  safety guard агента; пользователь должен сгенерировать ключ, заменить `pubkey`,
  добавить secrets и собрать/запустить release workflow.
- [ ] GitHub Release и тег `v0.2.0` не создавались.

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
| `cargo check --manifest-path src-tauri/Cargo.toml` | ok (Tauri 2.12, dialog+updater) |
| `cargo test --manifest-path src-tauri/Cargo.toml` | 7 passed |
| `cargo test --manifest-path crates/tns-excel/Cargo.toml` | 5 passed |
| `cargo build --manifest-path crates/tns-parity/Cargo.toml` | ok |
| `.\scripts\verify.ps1 -RequireRustOutput` | All checks passed |
| `scripts/release-latest-json.ps1` | проверен на dummy `.nsis.zip`/`.sig` |
| `.github/workflows/*.yml` | YAML parsed; release не запускался без tag/secrets |
| live Tauri smoke (WebView2 CDP) | UI loaded; detect/process/results/history/backup ok |
| release build (unsigned NSIS) | `TNS Energy Studio_0.2.0_x64-setup.exe`, CDP smoke ok |
| `npm --prefix apps/ui ci` | ok (26 packages, lock sync) |
| `git diff parity-harness -- legacy/pyqt tests/parity/fixtures` | пусто |

## В работе

- Release 0.2.0: ключ updater, `pubkey`, GitHub secrets, подписанная сборка и
  первый тег `v0.2.0`; затем ручной smoke native file dialog и open file/folder.

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
- Updater `pubkey` в `src-tauri/tauri.conf.json` — placeholder. До первого релиза
  нужно сгенерировать minisign-ключ, заменить публичный ключ и добавить секреты
  `TAURI_SIGNING_PRIVATE_KEY`/`_PASSWORD`; без них release job падает. Локальная
  unsigned-сборка 0.2.0 уже проверена, но подписанные updater-артефакты не созданы.
- Release workflow не запускался: нет тега/секретов. После настройки ключа
  проверить `npx @tauri-apps/cli@2 build --bundles nsis`, наличие `*.nsis.zip.sig`
  и `latest.json`, затем создать тег `v0.2.0`.
- Authenticode-шаг опционален и подписывает `.exe` после Tauri bundling; для полной
  цепочки (подпись installer до updater-архива) нужен `bundle.windows.signCommand`.
  Текущий workflow — безопасный placeholder.

## Следующие шаги

1. Сгенерировать minisign-ключ Tauri, заменить `pubkey`, добавить GitHub secrets.
2. Собрать подписанные NSIS/updater-артефакты и проверить `latest.json`.
3. Создать и запушить тег `v0.2.0`; проверить GitHub Release.
4. Ручной smoke native file dialog, live-отмены и `open_file`/`open_folder`.
5. Финальный critic и визуальная приёмка на release-сборке.
