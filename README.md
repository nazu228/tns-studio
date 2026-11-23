# TNS Energy Studio — миграция на Rust + React + Tauri

TNS Energy Studio — десктопное приложение для обработки ведомостей энергосбыта
(Excel → расчёт → Excel). Legacy-версия на Python/PySide6 остаётся в
`legacy/pyqt/` как неизменяемый оракул.

Новый стек:

- **Rust core** — парсинг, расчёт, SQLite, Excel (`umya-spreadsheet`);
- **React + TypeScript + Vite** — UI с design parity;
- **Tauri 2** — десктопная оболочка, локальные команды, прогресс/отмена;
- **GitHub Releases** — обновления через Tauri updater; S3/Yandex не используются.

## Текущее состояние

- Parity-база: 3 golden-фикстуры, golden JSON/xlsx, 5 скриншотов legacy,
  независимый `xlsx_signature`.
- `crates/tns-core` — `process_statement` совпадает с golden по result и по
  полной xlsx-сигнатуре (значения, формулы, merge, freeze, стили, CF, hyperlink).
- `crates/tns-db` — локальная SQLite: история, дома, тарифы, бэкап.
- `crates/tns-pdf` — PDFium-парсер PDF-ведомостей (7a–7c): векторная сетка,
  только известный layout; CLI и приложение пишут стандартные xlsx по договору.
- `src-tauri` — реальные `detect_statement`/`process_statement`/`process_pdf`,
  прогресс `process-progress`, `cancel_statement`, запись истории, updater-плагин;
  PDFium DLL бандлится как resource.
- `apps/ui` — реальный Tauri IPC вместо мока: выбор файла/папки (`.xlsx`/`.pdf`),
  режимы both/dom/gorod, прогресс, отмена, результаты, история, бэкап, open file/folder.
- Проверки: **62 Rust-теста** (core 16, db 4, excel 7, tauri 9, pdf 26) и
  **22 pytest passed / 0 xfailed**.
- Релиз `0.2.0` опубликован как GitHub Release `v0.2.0-1`: NSIS installer,
  `.exe.sig` и `latest.json`; updater проверен через GitHub endpoint.

Живой runtime-smoke выполнен в Tauri-окне: расчёт из UI создал xlsx, полностью
совпадающий с golden; история и бэкап проверены. Ручная проверка нативного
диалога выбора файла/папки и `open_file`/`open_folder` остаётся на приёмке.

PDF-ведомости (CLI и приложение):

```powershell
cargo run -p tns-pdf -- parse "<pdf>" --xlsx "<out-dir>" [--json "<out-dir>"]
```

В приложении выбери `.pdf` как файл или папку с PDF: расчёт сам определит
ведомости, отфильтрует по режиму и создаст отдельные xlsx.

Имена выходов: `<contract>_<Month>_<Year>.xlsx`, корректировки —
`<contract>_<Month>_<Year>_за_<BaseMonth>_<BaseYear>.xlsx`; несколько ведомостей
в одном PDF пишутся отдельными файлами.

## Структура

```text
legacy/pyqt/        # эталон PySide6, не менять
crates/tns-core/    # парсинг, layout, writer, стили, process_statement
crates/tns-db/      # SQLite: schema/seed/history/backup/validate
crates/tns-excel/   # umya-обёртка, safe_save, xlsx post-processing
crates/tns-parity/  # Rust-драйвер для pytest
crates/tns-pdf/     # PDFium-парсер PDF + проекция на стандартную ведомость
src-tauri/          # Tauri shell и команды
apps/ui/            # Vite + React UI
tests/parity/       # golden, фикстуры, скриншоты, oracle
docs/               # план, инвентарь, parity-matrix, handoff
.github/workflows/  # CI и GitHub Release
```

## Зафиксированные решения

- UI — React/TS; ядро — Rust; оболочка — Tauri 2.
- Визуальный паритет: та же компоновка, цвета, шрифты, поведение; без редизайна.
- Данные — только локальная SQLite и локальные бэкапы. Облачной синхронизации нет.
- Обновления — только GitHub Releases + `latest.json` + Tauri updater.
- Подписи — minisign для updater и Authenticode для Windows.
- `legacy/pyqt/**` и `tests/parity/fixtures/**` не изменяются.

## Быстрый старт

```powershell
# UI-зависимости (после изменения package-lock)
npm --prefix apps/ui ci --no-audit --no-fund

# Полная проверка: UI build → Rust tests/check → parity → guard
.\scripts\verify.ps1 -RequireRustOutput

# Отдельно Tauri-тесты
cargo test --manifest-path src-tauri/Cargo.toml

# Разработка UI
npm --prefix apps/ui run dev
```

`verify.ps1` сначала собирает `apps/ui/dist`, потому что `tauri::generate_context!`
читает `frontendDist` уже на этапе `cargo check`, затем гоняет все Rust-тесты,
parity-тесты и проверяет неизменность `legacy/pyqt`/golden. Скрипт использует
локальную ветку `parity-harness` для guard, если она существует.

Если `cargo` не находит `link.exe`, используйте `.\scripts\cargo.ps1` или
окружение MSVC Build Tools (`vcvars64.bat`).

## Legacy-эталон

```powershell
python legacy/pyqt/app_gui.py
```

Нужен Python 3.11+ с PySide6 и openpyxl. База создаётся автоматически.

## Parity-харнесс

```powershell
python tests/parity/scripts/gen_fixtures.py
python tests/parity/scripts/gen_golden.py
python tests/parity/scripts/gen_screenshots.py
python -m pytest tests/parity -q
```

Фикстуры: `dom_april_2026.xlsx`, `gorod_april_2026.xlsx`,
`dom_march_2026.xlsx`. Полный xlsx-сигнал сравнивается с golden через openpyxl;
Rust-драйвер `crates/tns-parity` — отдельный процесс, не Rust-экстрактор.

## Updater и GitHub Releases

Релиз запускается тегом `v*` (например, `v0.2.0`). Workflow
`.github/workflows/release.yml` собирает NSIS-установщик и updater-артефакты
в `target/release/bundle/nsis`, генерирует `latest.json` и публикует GitHub
Release. Endpoint в `src-tauri/tauri.conf.json`:

```text
https://github.com/nazu228/tns-studio/releases/latest/download/latest.json
```

`pubkey` в `plugins.updater` уже установлен (commit `8f9ab17`); для ротации замените его новым публичным ключом.
Приватный ключ и пароль **не коммитятся**. Перед первым релизом/ротацией:

1. Сгенерируйте minisign-ключ Tauri:
   `npx --yes @tauri-apps/cli@2 signer generate -w $env:USERPROFILE\.tauri\tns-0.2.0.key`.
2. Проверьте, что `pubkey` в `src-tauri/tauri.conf.json` соответствует ключу; для новой пары — замените.
3. Добавьте GitHub Actions secrets:
   - `TAURI_SIGNING_PRIVATE_KEY` — содержимое приватного ключа (или путь, который
     доступен runner'у; для GitHub надёжнее содержимое);
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` — пароль ключа;
   - `WINDOWS_CERTIFICATE` — base64 PFX для Authenticode (опционально);
   - `WINDOWS_CERTIFICATE_PASSWORD` — пароль PFX.
4. Создайте и запушьте тег `v0.2.0`.

Локальная проверка подписанной сборки (после шага 1):

```powershell
$env:TAURI_SIGNING_PRIVATE_KEY = Get-Content $env:USERPROFILE\.tauri\tns-0.2.0.key -Raw
$env:TAURI_SIGNING_PRIVATE_KEY_PASSWORD = "<пароль ключа>"
npx --yes @tauri-apps/cli@2 build --bundles nsis
$asset = Get-ChildItem target\release\bundle\nsis\*-setup.exe | Select-Object -First 1
.\scripts\release-latest-json.ps1 -Version 0.2.0 -Tag v0.2.0 `
  -AssetPath $asset.FullName -SignaturePath "$($asset.FullName).sig" `
  -OutputPath latest.json -Notes (Get-Content RELEASE_NOTES.md -Raw -Encoding UTF8)
```

Без `TAURI_SIGNING_PRIVATE_KEY` (или при placeholder `pubkey`) release job падает до сборки. `latest.json`
содержит `version`, `notes`, `pub_date` и `platforms.windows-x86_64` с
подписью и URL на `*-setup.exe`.

Authenticode-шаг опционален, но подписывает `.exe` после Tauri и делает
сгенерированный `.exe.sig` недействительным. Для полной цепочки настройте
`bundle.windows.signCommand`, чтобы Authenticode применялся до updater-подписи;
без сертификата оставьте `WINDOWS_CERTIFICATE` пустым.

Yandex/S3/cloud sync не используются; `latest.json` и все артефакты лежат
только в GitHub Releases.

Release notes: `RELEASE_NOTES.md` (workflow кладёт их в тело GitHub Release и
в `latest.json`).

## Handoff и карта кода

- `docs/HANDOFF_PROMPT.md` — полный промпт для нового чата/агента.
- `docs/status.md` — фактический статус миграции.
- `graphify-out/GRAPH_REPORT.md` — карта кода.
- `graphify-out/graph.html` — интерактивная карта.
- `graphify-out/graph.json` — граф для `graphify query/path/explain`.

```powershell
graphify query "как process_statement связан с tns-db?"
graphify update .   # после изменений кода
```

## Ветки

- `main` — legacy-снапшот.
- `rust-migration` — план миграции.
- `parity-harness` — текущая ветка миграции; срезы 1–6 смержены, релиз `0.2.0`
  опубликован как `v0.2.0-1`, ветка запушена. Старый тег `v0.2.0` не содержит релиза.
