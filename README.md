# TNS Energy Studio — миграция на Rust + React + Tauri

TNS Energy Studio — десктопное приложение для обработки ведомостей энергосбыта
(Excel → расчёт → Excel). Текущая версия написана на Python/PySide6.

Этот репозиторий — рабочая площадка миграции на новый стек:

- **Rust core** (логика, SQLite, Excel, обновления)
- **React + TypeScript + Vite** (UI, design parity с текущим приложением)
- **Tauri 2** (десктопная оболочка)
- **GitHub Releases** (обновления вместо Yandex Object Storage)

## Структура

```
legacy/pyqt/        # эталон: текущий исходник PySide6 (не менять, это оракул)
crates/             # Rust workspace (создаётся в ходе миграции)
src-tauri/          # Tauri shell (создаётся в ходе миграции)
apps/ui/            # Vite + React UI (создаётся в ходе миграции)
tests/parity/       # pytest: golden-файлы, скриншоты legacy, контракты
docs/               # план миграции, инвентарь, матрица паритета
.github/workflows/  # CI: build, test, release на GitHub
```

## Зафиксированные решения

Полный список — в `docs/TNS_MIGRATION_PLAN.md`. Коротко:

- UI — React/TS (не Rust); ядро — Rust; оболочка — Tauri 2.
- Визуальный паритет: near-pixel (та же компоновка, цвета, шрифты, поведение; ±2px).
- Данные — только локальная SQLite + локальные бэкапы. Облачная синхронизация (S3/Yandex) удалена.
- Обновления — только GitHub: Releases + `latest.json` + Tauri updater. Yandex не используется.
- Подписи: minisign (updater) + Authenticode (Windows).
- No-code слой — позже. TMZ и WaterMetrics — после TNS.

## Как запустить legacy-эталон

```powershell
python legacy/pyqt/app_gui.py
```

Нужен Python 3.11+ с PySide6, openpyxl. База создаётся и заполняется автоматически при первом запуске.
