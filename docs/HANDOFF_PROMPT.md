# HANDOFF PROMPT — TNS Energy Studio: миграция на Rust + React + Tauri

> Скопируй этот файл целиком в новый чат (или скажи агенту: «прочитай docs/HANDOFF_PROMPT.md и продолжай»).  
> Репозиторий: https://github.com/nazu228/tns-studio  
> Рабочая ветка: `parity-harness` (последний коммит на момент написания: `70c0726`).  
> Локальный путь: `C:\Users\admin\projects\tns-studio`.

---

## 1. Роль

Ты — senior-инженер по Rust, React/TypeScript и Tauri. Твоя задача — довести миграцию TNS Energy Studio с Python/PySide6 на Rust core + React UI + Tauri 2. Не начинай с нуля: в репозитории уже есть рабочая база, golden-тесты и план. Сначала прочитай:

1. `docs/TNS_MIGRATION_PLAN.md` — полный план и решения.
2. `docs/status.md` — что уже сделано.
3. `docs/inventory.md` — контракты legacy.
4. `docs/parity-matrix.md` — матрица паритета.
5. `graphify-out/GRAPH_REPORT.md` — карта кода и сообществ.
6. `legacy/pyqt/` — эталон (только чтение).

---

## 2. Что за проект

TNS Energy Studio — Windows-приложение для обработки ведомостей энергосбыта: читает Excel, проверяет строки домов/приборов/субабонентов, считает начисления, формирует итоговый Excel и историю в SQLite.

Текущая версия — Python 3.11+/PySide6. Целевая:

- **Rust core** — расчёты, Excel, SQLite, обновления.
- **React + TypeScript + Vite** — UI, design parity с legacy.
- **Tauri 2** — десктопная оболочка.
- **GitHub Releases** — обновления вместо Yandex Object Storage.

---

## 3. Зафиксированные решения (не менять без пользователя)

| Решение | Значение |
|---|---|
| Ядро | Rust + Tauri 2 |
| UI | React + TypeScript + Vite; UI не на Rust |
| Визуал | Design parity, near-pixel: те же экраны/кнопки/цвета/размеры/поведение; ±2px; редизайн запрещён |
| Данные | Только локальная SQLite + локальные бэкапы; облачная синхронизация удалена |
| Yandex | Полностью убран: и обновления, и S3-sync |
| Обновления | GitHub only: Releases + `latest.json` + Tauri updater |
| Подписи | minisign (updater) + Authenticode (Windows) |
| Python | Переходный эталон; конечная точка — Python = 0 |
| No-code | Позже; сейчас не делать |
| Порядок | TNS первым; TMZ (с 1С UIA spike) и WaterMetrics — после |
| Репозиторий | Публичный `nazu228/tns-studio` |

---

## 4. Текущее состояние (факты)

Проверено на ветке `parity-harness`:

| Компонент | Состояние | Тесты |
|---|---|---|
| `tests/parity` | 3 фикстуры (dom/gorod/march), golden JSON+xlsx, 5 скриншотов legacy, независимый `xlsx_signature` | **22 passed, 0 xfailed** |
| `crates/tns-excel` | Обёртка `umya-spreadsheet` 3.1.1: чтение/запись, `safe_save`, узкие xlsx post-processors | **5 passed** |
| `crates/tns-core` | `normalize_header`, `row_type`, `safe_float`, `numeric_value`, `classify_zone`, `total_row`, `resolve_layout`, `extract_metadata`, `detect_statement_type`, `process_statement` (парсинг/итоги/result/прогресс/отмена) | **16 passed** |
| `crates/tns-core` output writer | срез 1+2: «Ведомость ЭП» + «Сводка по домам», формулы/merge/freeze/размеры/стили/CF/hyperlink/`safe_save` | full xlsx-golden 0 diffs на 3 фикстурах |
| `crates/tns-db` | Схема legacy, seed, история, upsert домов, локальный бэкап, валидация | **4 passed** |
| `src-tauri` | Tauri 2 shell, окно 1280×880, 9 команд; real `detect_statement`/`process_statement` (+cancel), progress, SQLite history/houses, dialog+updater plugins | **7 passed**, `cargo check` ok |
| `apps/ui` | React/Vite главное окно TNS, design parity; реальный Tauri IPC (`ipc.ts`), detect/process/progress/cancel/history/backup/open; моков и `setTimeout` нет | `typecheck` + `build` ok; full verify passed |

Итого **32 Rust-теста** и **22 pytest passed, 0 xfailed**. `process_statement` совпадает с golden по `result` на dom/gorod; writer совпадает по полному xlsx-сигналу на всех 3 фикстурах, включая стили/CF/hyperlink; Tauri-команды detect/process покрыты тестами на фикстурах и пишут историю в SQLite; UI вызывает их через `ipc.ts`, моков нет.

### Чего ещё нет

- **Updater/CI**: закрыто в срезе 5; release workflow требует secrets и ещё ни разу не запускался.
- **E2E/visual smoke**: живое Tauri-окно, прогресс/отмена/история, Playwright/скриншоты.
- **TNS/WaterMetrics**: после TNS.
- **No-code**: позже.

---

## 5. Карта репозитория

```
tns-studio/
  legacy/pyqt/                 # ЭТАЛОН, только чтение
  crates/
    tns-core/
      src/lib.rs               # чистые функции, TnsError, Zone
      src/layout.rs            # resolve_layout/extract_metadata/detect_statement_type
      src/process.rs           # process_statement (result/parse; output workbook — TODO)
    tns-excel/src/lib.rs       # umya wrapper: read/write/safe_save
    tns-db/src/lib.rs          # rusqlite: schema/seed/history/backup/validate
    src-tauri/
    src/main.rs                # Tauri commands: detect/process/cancel/history/backup/config
    tauri.conf.json            # window/frontendDist/bundle
    capabilities/default.json  # core:default + dialog:default
  apps/ui/
    src/App.tsx                # главное окно (design parity, реальный IPC)
    src/ipc.ts                 # типы + invoke/listen/dialog обёртки
    src/styles.css             # токены/тема + progress/history
    src/data.ts                # только MONTHS/YEARS (моки удалены)
  tests/parity/                # фикстуры, golden, скриншоты, pytest
  docs/                        # план, инвентарь, матрица, статус
  scripts/verify.ps1           # полная проверка
  scripts/cargo.ps1            # cargo с MSVC env
  graphify-out/                # карта кода (graph.json/html, GRAPH_REPORT.md)
```

---

## 6. Что делать дальше (порядок)

### Срез 1 — output workbook core (готов)
**Статус: закрыт**; layout-паритет на 3 фикстурах, 15 Rust-тестов. Ниже — исходная постановка для истории.
В `crates/tns-core/src/process.rs` + новый `src/output.rs`:
- сделать книгу изменяемой, переименовать исходный лист в «Ведомость ЭП»;
- создать лист «Сводка по домам» первым;
- записать значения и формулы SUM/ROUND/IF с теми же пробелами/кавычками, что в legacy;
- merge `A1:J1`, `A2:J2`, `A3:J3`; freeze `C6`; ширины/высоты;
- сохранить через `tns_excel::safe_save`, вернуть фактический `target_path` и `warning`;
- golden-тест: result + значения/формулы/merge/freeze/ширины против `tests/parity/fixtures/golden/*.xlsx`.
Стили/CF/hyperlink — следующий срез.

### Срез 2 — output styles (готов)
**Статус: закрыт**; полный `xlsx_signature` — 0 diffs на 3 фикстурах, pytest 22/0. Ниже — исходная постановка для истории.
`crates/tns-core/src/output_style.rs`:
- Segoe UI 9/10/13; заливки `FFF2CC/D9E1F2/E2EFDA/F2F2F2/BDD7EE/F2F4F7/1F4E79`;
- границы thin `D3D3D3` / double `1F4E79`; `#,##0.000`; alignment/wrap;
- CF `H6:Hn` equal/notEqual 0; hyperlink на «Ведомость ЭП»;
- квирки legacy: строка 10 может быть перезаписана первым ПУ; C/D/E/G сводки остаются Calibri 11; пустые зоны → 0.0, не формула.
Расширить golden-тест до полной xlsx-сигнатуры (`tests/parity/parity_lib.py::xlsx_signature`).

### Срез 3 — Tauri commands (готов)
**Статус: закрыт**; `cargo test src-tauri` — 7 passed, parity 22/0. Ниже — исходная постановка для истории.
`src-tauri/src/main.rs`:
- `detect_statement(path)` — файл/папка, dom/gorod/unknown, consumer/contract;
- `process_statement(...)` — `tns_core::process_statement` в `spawn_blocking`, прогресс через `emit("process-progress", {percent,message})`, отмена через `AtomicBool` + `cancel_statement`;
- запись `record_calculation`/`register_or_update_house` в `tns-db`;
- `backup_db`, `history_list`, `open_file`, `open_folder`, `config_get`;
- `tauri-plugin-dialog` + capabilities.
Тест `detect_statement` на dom/gorod фикстурах.

### Срез 4 — UI invoke (готов)
**Статус: закрыт**; `npm ci`, typecheck, build и полный `verify.ps1 -RequireRustOutput` — зелёные. `ipc.ts` — единый мост; App.tsx без моков/setTimeout; прогресс/отмена/история/бэкап/open работают через команды. Runtime-smoke в живом окне остаётся на e2e.
`apps/ui`:
- `@tauri-apps/api` + `@tauri-apps/plugin-dialog`;
- убрать `setTimeout`/мок; `invoke`/`listen`;
- detect/process/history/backup/open; прогресс/ошибка/отмена;
- режимы both/dom/gorod; дизайн не менять; кнопки «Облако» нет.
`npm run typecheck && npm run build`.

### Срез 5 — updater/CI (готов)
**Статус: закрыт**; CI/release workflows, `latest.json`, updater-плагин и README готовы; release не запускался без tag/secrets.
- `src-tauri/Cargo.toml` + `main.rs`: `tauri-plugin-updater`, реальный async `update_check`;
- `src-tauri/tauri.conf.json`: `plugins.updater.endpoints`, `createUpdaterArtifacts: true`, `pubkey` placeholder;
- `capabilities/default.json`: `updater:default`;
- `.github/workflows/ci.yml`: Windows, Node/Python/Rust, `verify.ps1 -RequireRustOutput`;
- `.github/workflows/release.yml`: tag `v*`, NSIS + updater zip, optional Authenticode, `latest.json`, GitHub Release;
- `scripts/release-latest-json.ps1`: `windows-x86_64` signature+URL;
- README: секреты, ключи, подписи, только GitHub Releases.

### Срез 6 — e2e/critic (следующий)
Прогнать живое Tauri-окно, проверить detect/process/прогресс/отмену/историю/open, визуальный smoke, golden-паритет, отсутствие S3/Yandex/sync, неизменность `legacy/pyqt` и `tests/parity`, дизайн и коммиты.

---

## 7. Жёсткие ограничения

- `legacy/pyqt/` — только чтение, это оракул.
- `tests/parity/` и `tests/parity/fixtures/golden/` — не менять.
- TMZ и WaterMetrics — не трогать.
- No-code — не делать.
- S3/Yandex/cloud sync — не добавлять; данные только локально.
- Обновления — только GitHub.
- Редизайн UI запрещён; кнопки «Облако»/S3 быть не должно.
- В `main` не пушить; работать в ветке/worktree.
- Секреты не коммитить.

---

## 8. Верификация

Каноническая команда (обычная проверка):

```powershell
.\scripts\verify.ps1
```

Release gate для полного xlsx-паритета (обязателен после среза 2):

```powershell
.\scripts\verify.ps1 -RequireRustOutput
```

Скрипт ставит `apps/ui/node_modules` при необходимости, собирает UI до `cargo check src-tauri` (иначе `generate_context!` не найдёт `frontendDist`) и гоняет:

```powershell
npm --prefix apps/ui run typecheck
npm --prefix apps/ui run build
cargo test --manifest-path crates/tns-core/Cargo.toml
cargo test --manifest-path crates/tns-db/Cargo.toml
cargo test --manifest-path crates/tns-excel/Cargo.toml
cargo test --manifest-path src-tauri/Cargo.toml
cargo check --manifest-path src-tauri/Cargo.toml
cargo build --manifest-path crates/tns-parity/Cargo.toml
python -m pytest tests/parity -q
git diff --exit-code parity-harness -- legacy/pyqt tests/parity/fixtures
```

Release (tag `v*`) выполняет `.github/workflows/release.yml`: verify, `npx @tauri-apps/cli@2 build --bundles nsis`, updater-подпись, `latest.json`, GitHub Release. Локально release не запускается.

Guard использует локальную базу `parity-harness`, потому что `origin/parity-harness` может быть устаревшим до push. В CI после push можно сравнивать с `origin/parity-harness`.

Если `cargo` не находит `link.exe` — используй `.\scripts\cargo.ps1` или окружение MSVC Build Tools (`vcvars64.bat`). UI `dist` не коммитить.

---

## 9. Известные ловушки (проверено на практике)

1. **umya-spreadsheet tuple coordinates — `(column, row)`**, не `(row, column)`. В `tns-core/src/layout.rs` есть helper `cell()` с комментарием.
2. **`book.sheet(0)` возвращает `Result<&Worksheet, XlsxError>`**, не `Option`.
3. **`process_statement` consumer**: legacy возвращает hardcoded `ООО "Южный Дом"` и `ООО "Южный город"` (строчные кавычки/регистр), не исходную строку из шапки.
4. **Golden `preview_rows`**: Python отдаёт `0` (int), Rust — `0.0`; сравнивать числа с допуском, не `serde_json::Value` напрямую.
5. **`safe_save` warning** дословно: `Основной файл открыт в Excel; результат сохранен в отдельную копию.`
6. **Ошибки legacy** — дословно русские; не переписывать.
7. **`scripts/cargo.ps1` под PowerShell 5.1** может спотыкаться на stderr cargo; `scripts/verify.ps1` — предпочтительный вход.
8. **Squad**: агенты уже трижды падали на больших срезах (лимит шагов, пустой отчёт без коммита). Давай маленькие задачи, требуй коммит после каждого файла/теста; отчёт без коммита = failed.
9. **`apps/ui/data.ts`** — только `MONTHS`/`YEARS`; моки удалены. Не возвращать mock rows в UI, данные приходят из `ProcessResult`.
10. **`src-tauri/gen/schemas/*`** может перегенерироваться `cargo check` с LF; не коммить случайные EOL-изменения.
11. **Xlsx-гейт**: layout `include_styles=False` и полный `xlsx_signature` enforced; полный gate запускается `scripts/verify.ps1 -RequireRustOutput`. Пропавший output — всегда hard fail, style/CF/hyperlink diff при `TNS_REQUIRE_RUST_OUTPUT=1` — fail. Не ослаблять тесты.
12. **umya ширины**: соседние `<col>` с одинаковой шириной coalesce; writer сдвигает вторую на `1e-7`, openpyxl `round(6)` это скрывает. Не убирать хак без замены.
13. **Multi-sheet**: writer/parser используют `book.sheet(0)`, legacy — `wb.active`; порядок сводки для extra-листов исправлен, active-sheet вход пока не поддержан.
14. **umya пустой `<diagonal/>`**: при любом border umya пишет пустой diagonal, openpyxl видит `Side(None,None)` вместо `None`. `tns-excel` удаляет пустой diagonal только у границ со стилем; не удалять у borderless-ячеек.
15. **Пустая A итоговой строки**: legacy/openpyxl пишет `t="inlineStr"`; umya — numeric. `tns-excel` ставит `t="inlineStr"` только для переданной пустой координаты (A{6+houses.len()}). Не превращать это в общий inline-string writer без тестов.
16. **Tauri IPC**: JS-аргументы camelCase (`sourcePath`, `outputDir`, `customFilename`); прогресс — событие `process-progress` с `{percent, message}`; `detect_statement` для папки отдаёт `files`, `kind` агрегируется только при единогласии; ошибка SQLite не валит сохранённый расчёт, а добавляет `history_warning`.
17. **UI IPC**: payload-поля Rust остаются snake_case (`is_dir`, `preview_rows`, `history_warning`), аргументы JS — camelCase. Весь обмен — через `apps/ui/src/ipc.ts`; не возвращать моки/setTimeout. После изменения `package.json`/lock нужен `npm --prefix apps/ui ci`, иначе старые `node_modules` не увидят новые deps.
18. **UI runtime**: typecheck/build не проверяют живое окно; перед релизом нужен smoke в Tauri (detect/process/прогресс/отмена/история/open).
19. **Updater ключи**: `plugins.updater.pubkey` — placeholder. Для релиза нужен minisign-ключ, замена pubkey и secrets `TAURI_SIGNING_PRIVATE_KEY`/`_PASSWORD`; без них release job падает. `latest.json` лежит на `releases/latest/download/latest.json`.
20. **Release workflow**: tag `v*` → NSIS + `*.nsis.zip` + `.sig`; `scripts/release-latest-json.ps1` собирает `windows-x86_64`. Authenticode-шаг подписывает `.exe` после bundling; для полной цепочки нужен `bundle.windows.signCommand`. Release ни разу не запускался без tag/secrets.
21. **CI порядок**: `generate_context!` читает `apps/ui/dist` на этапе cargo, поэтому `verify.ps1` сначала делает `npm typecheck/build`, затем `cargo test/check src-tauri`; `cargo test src-tauri` включён в скрипт. После изменения lock — `npm ci`.

---

## 10. Graphify (карта кода)

В репозитории есть `graphify-out/`:

- `graph.json` — граф (942 узла, 2033 ребра, 47 сообществ на момент сборки);
- `graph.html` — интерактивная карта;
- `GRAPH_REPORT.md` — отчёт: god nodes, связи, сообщества, циклы;
- `manifest.json` — манифест для `--update`.
...

Команды:

```powershell
graphify query "как process_statement связан с tns-db?"
graphify path "process_statement" "tns-db"
graphify explain "process_statement"
graphify update .          # после изменений кода, без LLM
```

Карта обновлена после среза 4; после правок запусти `graphify update .`.

---

## 11. Первый шаг нового чата

1. Прочитай `docs/HANDOFF_PROMPT.md`, `docs/status.md`, `graphify-out/GRAPH_REPORT.md`.
2. Обнови UI-зависимости (`npm --prefix apps/ui ci`, если менялся lock) и запусти `.\scripts\verify.ps1 -RequireRustOutput` — база: 32 Rust-теста, 22 pytest passed / 0 xfailed, UI typecheck/build.
3. Возьми **срез 6 (e2e/visual smoke + critic)**. Не пытайся закрыть всё сразу.
4. После каждого файла/теста — коммит. После среза — `cargo test` + `pytest` + `graphify update .`; финальный gate — `.\scripts\verify.ps1 -RequireRustOutput`.
5. Если поведение legacy неоднозначно — читай `legacy/pyqt/core_engine.py` и `tests/parity/parity_lib.py`, не выдумывай.

**Цель**: TNS Energy Studio, полностью работающая на Rust + React + Tauri, с golden-паритетом, локальными данными и GitHub-обновлениями.
