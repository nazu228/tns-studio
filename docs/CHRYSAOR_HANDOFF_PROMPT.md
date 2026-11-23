# HANDOFF PROMPT — Chrysaor / TMZ Studio: переделка на Rust + React + Tauri

> Скопируй этот файл целиком в новый чат или скажи агенту:  
> «Прочитай `docs/CHRYSAOR_HANDOFF_PROMPT.md` и продолжай миграцию Chrysaor».
>
> Репозиторий: `nazu228/tmz-studio` (**private**).  
> Канонический исходник: `C:\Users\admin\Documents\Codex\2026-10-19\new-chat-2\work\tmz-source`.  
> Установленная копия (только чтение, эталон поведения): `C:\Users\admin\AppData\Local\Programs\TMZ_Studio`.  
> Референс миграции TNS: `C:\Users\admin\projects\tns-studio`, ветка `parity-harness`, файл `docs/HANDOFF_PROMPT.md`.

---

## 1. Роль и миссия

Ты — senior-инженер по Rust, React/TypeScript, Tauri 2 и Windows-автоматизации. Твоя задача — перевести **Chrysaor / TMZ Studio** с Python + QWebEngine на **Rust core + React UI + Tauri 2**, сохранив визуал и поведение near-pixel. Это не редизайн и не «написать заново». Это strangler-миграция: Python API остаётся, пока его endpoint’ы по одному заменяются Rust-модулями.

Главный риск — не UI и не Excel, а **1С-автоматизация**: `autopilot_windows.py` (UIA/COM/ctypes) и `capture_1c.py` (GDI). Её нельзя портировать «по пути». Сначала — отдельный Rust spike на одном реальном окне 1С. Если Rust UIA не тянет — оставляем минимальный native sidecar, а не убиваем продукт.

---

## 2. Что читать в первую очередь

1. `app.py` — HTTP-сервер, все `/api/*`, статика, порт 8765.
2. `static/index.html` — все экраны: editor, preview, guide, autopilot, cloud sync modal, HUD.
3. `static/js/app.js` — основной UI/состояние.
4. `static/js/autopilot.js` — автопилот, очередь, HUD, шаги.
5. `static/js/sync_ui.js` — облачная синхронизация (удаляем).
6. `static/styles/tokens.css` — токены темы; `components.css`, `main.css`, `autopilot.css`, `animations.css`.
7. `autopilot_windows.py` — WinAPI/UIA/COM, самый тяжёлый модуль.
8. `capture_1c.py` — GDI-скриншоты/фокус окна 1С.
9. `sara_console.py` — нативная консоль Sara на QPainter (не первый wave).
10. `app_gui.py` — PySide6 `QWebEngineView`-оболочка.
11. `excel_engine.py`, `molodezhka_engine.py`, `district_geometry.py`, `manual_marks.py`, `database_safety.py`.
12. `sync_manager.py`, `cloud_sync.py`, `sync_config.json`, `updater.py`, `windows_update.py` — всё, что связано с Yandex/S3, выпиливаем.
13. `docs/CHRYSAOR_HANDOFF_PROMPT.md` — этот файл; `docs/TNS_MIGRATION_PLAN.md` и `docs/HANDOFF_PROMPT.md` в TNS-репо — как шаблон структуры и parity harness.

**Важно:** исходник в `tmz-source` неполный. В установленной копии есть файлы, которых нет в снапшоте (`app_gui.py`, `capture_1c.py`, `capture_frameless.py`, `cloud_sync.py`, `database_safety.py`, `district_geometry.py`, `excel_engine.py`, `launcher_chrysaor.py`, `local_api_guard.py`, `manual_marks.py`, `publish_release.py`, `report_workspace.py`, `sara_console.py`, `sync_config.json`, `sync_manager.py`, `ui_sync_components.py`, `updater.py`, `windows_update.py`). Сначала сверь и зафиксируй полный срез в `legacy/`, иначе миграция начнётся с дырами.

---

## 3. Факты об архитектуре Chrysaor

- UI — **уже веб**: `static/index.html` + JS/CSS, открывается в `QWebEngineView`. Главное окно — 1280×880 (проверь фактический размер).
- Локальный HTTP-сервер: `ThreadingHTTPServer` на `127.0.0.1:8765`, `SimpleHTTPRequestHandler` для статики; есть `find_free_port(8765)`.
- Экраны/табы: **editor**, **preview**, **guide**, **autopilot**; облачная модалка (overview/settings/diagnostics), HUD автопилота, консоль Sara.
- API (зафиксировать golden-ответами):
  - GET: `/api/config`, `/api/demo`, `/api/history`, `/api/clipboard`, `/api/updater/check`, `/api/sync/status`, `/api/sync/db-progress`, `/api/sync/download-progress`, `/api/sync/config`, `/api/autopilot/state`, `/api/autopilot/history`, `/api/autopilot/targets`, `/api/autopilot/queue`, `/api/autopilot/catalog`, `/api/autopilot/articles`.
  - POST: `/api/validate`, `/api/generate`, `/api/open-file`, `/api/open-folder`, `/api/window-action`, `/api/sync/check`, `/api/sync/download-update`, `/api/sync/cancel-download`, `/api/sync/apply-update`, `/api/sync/db/pull`, `/api/sync/db/push`, `/api/sync/diagnostics`, `/api/sync/config`, `/api/autopilot/load`, `/api/autopilot/upload`, `/api/autopilot/teach`, `/api/autopilot/undo-teach`, `/api/autopilot/import-catalog`, `/api/autopilot/reconcile`, `/api/autopilot/recover`, `/api/autopilot/bind`, `/api/autopilot/start`, `/api/autopilot/step-action`.
- Статика (текущие размеры): `index.html` ~53KB; `app.js` ~26KB, `autopilot.js` ~75KB, `sync_ui.js` ~38KB, `editor_sync.js` ~7KB, `motion.js` ~7.5KB, `spreadsheet.js` ~6.4KB, `audio.js` ~3.8KB; CSS: `tokens.css` ~3.8KB, `components.css` ~23KB, `main.css` ~20KB, `autopilot.css` ~20KB, `animations.css` ~3.5KB.
- Backend: Python 3, PySide6, QWebEngine, `ctypes`/`win32`/COM/UIA, `sqlite3`, `openpyxl`, `QThread`/`QTimer`, `QPainter`.
- Обновления и синхронизация БД сейчас — **Yandex Cloud Object Storage** (`storage.yandexcloud.net`, bucket `ajeftdaam8hhmrujr94k`, region `ru-central1`); `sync_config.json` содержит DPAPI-блоб. Всё это удаляется.
- Репозиторий `nazu228/tmz-studio` — private. Не публиковать пользовательские данные/секреты. Установленную копию не редактировать.

---

## 4. Зафиксированные решения (не менять без пользователя)

| Решение | Значение |
|---|---|
| Стек | Rust core + React/TypeScript + Vite + Tauri 2 |
| UI | React; не Rust. Дизайн — near-pixel parity, ±2px, без редизайна |
| Данные | Только локальная SQLite + локальные бэкапы; облачная синхронизация удаляется |
| Yandex/S3 | Полностью убрать: и обновления, и sync |
| Обновления | GitHub Releases + `latest.json` + Tauri updater |
| Подписи | minisign + Authenticode (сертификат покупается) |
| Python | Остаётся на переходный период; конечная цель — Python = 0 |
| Порядок | TNS уже мигрируется; Chrysaor — следующий; WaterMetrics — после |
| 1С | Сначала Rust spike; при провале — минимальный native sidecar |
| No-code | Позже; сейчас не делать. Визуальный no-code — отдельный продукт |
| Next.js | Не использовать для десктопа; Vite. Next.js только если появится веб-версия |

---

## 5. Целевая архитектура

```
Chrysaor/
  apps/ui/                  # React + Vite + TS, дизайн-паритет
  src-tauri/                # Tauri 2 shell, commands, updater, capabilities
  crates/
    chrysaor-core/          # валидация, генерация, модели, ошибки
    chrysaor-excel/         # чтение/запись xlsx (umya-spreadsheet/calamine)
    chrysaor-db/            # rusqlite, схема, миграции, бэкапы
    chrysaor-1c/            # WinAPI/UIA/GDI: окна, контролы, скриншоты
    chrysaor-autopilot/     # состояние, очередь, шаги, восстановление
  legacy/pyqt/              # снимок Python-версии, только чтение
  tests/parity/             # golden API/Excel/DB + скриншоты
  docs/
  scripts/verify.ps1
```

Переходный вариант: React в Tauri вызывает `invoke` для уже портированных команд и `fetch` к Python API на 8765 для ещё не портированных. По мере портирования `fetch`-вызовы заменяются на `invoke`. Python-сервер можно запускать как sidecar Tauri, пока не умрёт последний endpoint.

---

## 6. Стратегия: вертикальные срезы, не big bang

Нельзя одновременно переписать UI, backend, 1С, Excel, БД, updater и выпилить Python. Это четыре конфликтующих проекта. Работаем срезами, каждый срез заканчивается зелёными тестами и коммитом.

### Phase 0 — Baseline и безопасность
- Сверить `tmz-source` с установленной копией; скопировать отсутствующие файлы в `legacy/pyqt/` (или `legacy/python/`), зафиксировать хэши.
- Запустить legacy на тестовой БД; снять скриншоты всех экранов/состояний (editor empty/filled, preview, guide, autopilot idle/running/error, cloud modal, HUD, Sara).
- Снять golden-ответы API на фикстурах; сохранить Excel-выходы и SQLite-фикстуры.
- Создать `tests/parity` и `scripts/verify.ps1` по образцу TNS.
- **Ничего не менять в legacy и установленной копии.**

### Phase 1 — Репозиторий и React-каркас
- Ветка от текущей default (не в `main`); worktree.
- `apps/ui`: Vite + React 19 + TS; перенести `tokens.css` и базовые стили; React-роутер/табы editor/preview/guide/autopilot.
- Сначала **editor** и **preview** на моках; Playwright-скриншоты против legacy; допуск ±2px/небольшой diff.
- Не трогать autopilot UI, пока не готов API-контракт.

### Phase 2 — API contract freeze
- Для каждого `/api/*` — golden JSON (успех/ошибка/пусто/крайние случаи).
- Типизированный клиент в UI: `api.ts` с union `invoke | fetch`.
- Порядок портирования: `/api/config`, `/api/validate`, `/api/generate`, `/api/history`, `/api/open-file`, `/api/open-folder`, `/api/window-action`; затем autopilot; sync-эндпоинты **удалить**, не портировать.
- Rust: Tauri commands или Axum — решить по месту; для десктопа предпочтительны commands.

### Phase 3 — Rust core: Excel/DB/config
- `chrysaor-excel`: чтение/запись существующих книг, сохранение формул/стилей; `safe_save` с fallback, если файл открыт в Excel.
- `chrysaor-db`: схема, миграции, бэкапы, `PRAGMA integrity_check`; без `sync_metadata`.
- `chrysaor-core`: валидация, генерация, модели, ошибки; golden-тесты.
- Перенести `excel_engine.py`, `molodezhka_engine.py`, `district_geometry.py`, `manual_marks.py`, `database_safety.py`.

### Phase 4 — 1С spike (критический)
- Отдельный Rust bin/test: найти окно 1С, построить UIA-дерево, прочитать контрол, нажать кнопку, снять скриншот GDI.
- Проверить на реальной сессии 1С, сравнить с Python-поведением.
- Если UIA-дерево/контролы недоступны или нестабильны — **стоп**: спроектировать sidecar (Python/маленький native helper) и продолжать UI/core без autopilot.
- Не портировать `autopilot_windows.py` целиком до успеха spike.

### Phase 5 — Autopilot
- `chrysaor-autopilot`: состояние, очередь, шаги, таймауты, восстановление, отмена, логирование.
- Перенести `autopilot_core.py`, `autopilot_driver.py`, `autopilot_driver_v2.py`, `autopilot_windows.py`.
- HUD и очередь — на React; прогресс/события — через Tauri events.
- Golden: сценарии autopilot на тестовом 1С/моках; никаких «магических» sleep без таймаутов.

### Phase 6 — Tauri shell, updater, packaging
- `src-tauri`: окно 1280×880, `frontendDist ../apps/ui/dist`, capabilities, dialog/updater plugins.
- Python sidecar только для непортированных частей; убрать, когда Python = 0.
- GitHub Actions: windows-latest, cargo test, npm ci/build, tauri build, minisign, Authenticode placeholders, GitHub Release + `latest.json`.
- `tauri.conf.json`: updater endpoint `https://github.com/nazu228/tmz-studio/releases/latest/download/latest.json`, `createUpdaterArtifacts: true`, pubkey placeholder.
- Удалить `sync_manager.py`, `cloud_sync.py`, `sync_ui.js`, `sync_config.json` из целевой сборки; миграция данных — только локальная.

### Phase 7 — Sara console и хвосты
- `sara_console.py` (QPainter) — последним: либо React/Canvas, либо оставить native-компонент.
- Удалить Python, когда все endpoint’ы и сценарии покрыты; финальный parity-прогон.

---

## 7. Критические риски и fallback

1. **1С UIA/COM** — главный риск. Rust `windows` + `uiautomation` может не дать тот же доступ/стабильность. Spike до autopilot. Fallback: sidecar.
2. **QWebEngine → Tauri WebView2** — различия в JS/CSS/шрифтах/скролле. Playwright-скриншоты, `tokens.css`, фиксированные размеры.
3. **Excel** — openpyxl-поведение (формулы, стили, объединения, CF). Golden xlsx-сигнатура, как в TNS.
4. **Данные** — SQLite-схема и локальные пути; не тащить S3/DPAPI. Секреты — Windows Credential Manager или ручной ввод.
5. **Обновления** — GitHub-only; в РФ возможны проблемы доступности, это принято. Не возвращать Yandex.
6. **Python sidecar** — не тащить в финал; только временный мост.

---

## 8. Верификация

Каждый срез:

```powershell
cargo test --manifest-path crates/chrysaor-core/Cargo.toml
cargo test --manifest-path crates/chrysaor-db/Cargo.toml
cargo test --manifest-path crates/chrysaor-excel/Cargo.toml
cargo check --manifest-path src-tauri/Cargo.toml
python -m pytest tests/parity -q
npm --prefix apps/ui run typecheck
npm --prefix apps/ui run build
```

Плюс:

- Playwright: legacy vs React screenshots, все состояния; diff не больше согласованного порога.
- Golden API: каждый endpoint — success/error/empty.
- Golden Excel: значения, формулы, стили, merge, freeze, CF, hyperlink.
- SQLite: схема/данные/бэкап/восстановление.
- Autopilot: сценарии на тестовом 1С или моках; отмена/таймаут/восстановление.
- Updater: `latest.json`, подпись, установка, откат.
- `git diff --exit-code` на `legacy/` и `tests/parity/` — эталон не менялся.

---

## 9. Жёсткие ограничения

- `legacy/` и `tests/parity/` — только чтение.
- Установленную `TMZ_Studio` не редактировать.
- Никакого редизайна; кнопки «Облако»/S3 в целевой версии нет.
- Никаких S3/Yandex/cloud sync; данные только локально.
- Обновления только GitHub.
- No-code сейчас не делать.
- WaterMetrics не трогать.
- Секреты/пользовательские данные не коммитить.
- Не пушить в `main`; работать в ветке/worktree.
- Не начинать с Sara console и не начинать с полного autopilot.

---

## 10. Известные ловушки

1. **Исходник неполный** — сверь `tmz-source` с установленной копией; иначе потеряешь `capture_1c.py`, `app_gui.py`, `sara_console.py` и др.
2. **Кодировка** — Python/HTML/JS могут быть в UTF-8 без BOM; PowerShell 5.1 показывает кириллицу как mojibake. Проверяй в браузере/редакторе, не «исправляй» кодировку вслепую.
3. **Порт 8765** — `find_free_port`; в тестах не полагайся на фиксированный порт.
4. **QWebEngine** — `QWebEngineView` грузит локальный URL; при Tauri — WebView2, другие devtools/шрифты/скролл.
5. **1С** — окна могут быть дочерними/модальными; UIA-дерево зависит от версии 1С и прав; COM — только STA-поток.
6. **GDI-скриншоты** — DPI-awareness, multi-monitor, свернутое окно; проверяй на 100%/125%/150%.
7. **DPAPI** — `sync_config.json` не переносится между машинами/пользователями; не пытайся расшифровать, просто удали.
8. **Excel** — файл может быть открыт; `safe_save` должен писать копию и возвращать warning.
9. **Tauri 2** — capabilities/plugins; `frontendDist` и `devUrl`; не тащить Node-сервер в прод.
10. **Squad** — агенты падали на больших срезах; давай один файл/один тест, требуй коммит после каждого. Отчёт без коммита = failed.

---

## 11. Правила для squad

Перед любым `/squad` или `squad` tool — **загрузи skill `squad`** и составь структурный brief: роли, файлы, зависимости, acceptance, checks. Не запускай с одной строкой.

Для Chrysaor:

- Один срез = один вертикальный кусок (например, «портировать `/api/validate` + golden-тест»).
- Явно указывай file ownership; не давай двум агентам один файл.
- Требуй коммит после каждого файла/теста; проверяй `git log`, а не отчёт.
- Ветка/worktree на агента; base — текущая рабочая ветка, не `main`.
- Если агент упёрся в лимит шагов — срез слишком большой, дроби.

---

## 12. Первые действия нового чата

1. Прочитай этот файл, `app.py`, `static/index.html`, `autopilot_windows.py`, `capture_1c.py`.
2. Сверь `tmz-source` с `C:\Users\admin\AppData\Local\Programs\TMZ_Studio`; создай полный `legacy/`-снимок и `docs/inventory.md`.
3. Запусти legacy на тестовой БД; сними скриншоты и golden API.
4. Создай `tests/parity` + `scripts/verify.ps1` по образцу TNS.
5. Подними `apps/ui` (Vite/React/TS) + `src-tauri`; портируй **editor** и **preview** на моках с Playwright-паритетом.
6. Заморозь `/api/config`, `/api/validate`, `/api/generate`; портируй в Rust с golden-тестами.
7. Сделай **1С UIA spike** до любого autopilot-кода.
8. Только после этого — autopilot, updater, удаление Python.

**Цель:** Chrysaor, полностью работающий на Rust + React + Tauri, с тем же визуалом и поведением, локальными данными и обновлениями только через GitHub. Не начинай с «переписать всё». Начни с сохранения эталона и одного зелёного среза.
