# Статус миграции TNS Energy Studio

Обновлено: 2026-11-16. Ветка: `parity-harness` (от `rust-migration`).

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
  - pytest-харнесс: **7 passed**.

### Phase 1 — скелет
- [x] `apps/ui` — Vite + React + TS, главное окно TNS (design parity):
  шапка, режимы, источник, месяц/год, карточки, вкладки, таблица, итоги, справка.
  Кнопка «Облако» и S3-бейдж удалены. `npm run typecheck` и `npm run build` проходят.
- [x] `crates/tns-core` — Rust-порт чистых функций:
  `normalize_header`, `row_type`, `safe_float`, `numeric_value`, `classify_zone`, `total_row`.
  `cargo check` проходит; unit-тесты написаны.
- [ ] `cargo test` — ждёт установку MSVC Build Tools (link.exe).
- [ ] Tauri shell, команды, updater, CI — следующий этап.

## Проверки

| Проверка | Результат |
|---|---|
| `python -m pytest tests/parity -q` | 7 passed |
| `cd apps/ui && npm run typecheck` | ok |
| `cd apps/ui && npm run build` | ok (dist) |
| `cargo check --manifest-path crates/tns-core/Cargo.toml` | ok |
| `cargo test --manifest-path crates/tns-core/Cargo.toml` | blocked: `link.exe` not found |
| `git diff origin/rust-migration -- legacy/pyqt` | пусто |

## В работе

- Установка Visual Studio Build Tools (workload VCTools + Windows SDK).
  После неё: `cargo test`, затем Tauri-скелет и интеграция UI с Rust-командами.

## Известные девиации

- Облачная синхронизация и Yandex удалены по решению; UI не содержит кнопку «Облако».
- React UI пока на моковых данных; реальные данные появятся после Tauri-команд.
- Скриншоты legacy сняты на Windows-платформе (Segoe UI, кириллица); на другой машине
  пиксельный diff может отличаться — сравнивать с эталоном этой машины.

## Следующие шаги

1. Дождаться Build Tools → `cargo test` для `tns-core`.
2. `crates/tns-db` (rusqlite): схема, seed, бэкап, история.
3. `crates/tns-excel`: чтение/запись xlsx, golden-паритет.
4. `src-tauri`: shell, 8 команд, прогресс/отмена, updater.
5. Интеграция React UI с Tauri-командами; Playwright visual diff.
6. GitHub Actions release + minisign + Authenticode.
