#!/usr/bin/env python3
"""Capture legacy TNS screenshots for visual parity.

The legacy window is instantiated from a temporary copy of legacy/pyqt so its
SQLite writes never touch the read-only reference tree. Output:
tests/parity/screenshots/*.png.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Use the native Windows platform so the system font database (Segoe UI,
# Cyrillic) is available; the window is moved off-screen before grabbing.
os.environ.setdefault("QT_QPA_PLATFORM", "windows")
os.environ.setdefault("PYTEST_QT_API", "pyside6")
os.environ.setdefault("TEST_MODE", "1")

PARITY_DIR = Path(os.environ.get("TNS_PARITY_DIR") or Path(__file__).resolve().parents[1]).resolve()
ROOT_DIR = PARITY_DIR.parents[1]
LEGACY_DIR = Path(os.environ.get("TNS_LEGACY_DIR") or (ROOT_DIR / "legacy" / "pyqt")).resolve()
SCREENSHOTS_DIR = PARITY_DIR / "screenshots"
GOLDEN_DIR = PARITY_DIR / "fixtures" / "golden"


def grab(widget, path: Path, app):
    app.processEvents()
    pixmap = widget.grab()
    pixmap.save(str(path))
    print(f"{path.name}: {pixmap.width()}x{pixmap.height()}")


def main() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tns-shots-") as tmp:
        legacy_copy = Path(tmp) / "pyqt"
        shutil.copytree(LEGACY_DIR, legacy_copy)
        sys.path.insert(0, str(legacy_copy))

        from PySide6.QtWidgets import QApplication, QMessageBox
        import app_gui

        # Never show modal boxes during offscreen capture.
        QMessageBox.information = staticmethod(lambda *a, **k: None)
        QMessageBox.warning = staticmethod(lambda *a, **k: None)
        QMessageBox.critical = staticmethod(lambda *a, **k: None)

        app = QApplication.instance() or QApplication([])
        window = app_gui.TNSEnergyStudioWindow()
        window.silent_check_updates = lambda: None
        window.resize(1280, 880)
        window.move(-3000, -3000)
        window.show()
        app.processEvents()

        grab(window, SCREENSHOTS_DIR / "main_empty.png", app)

        help_dialog = app_gui.AlgorithmHelpDialog(window)
        help_dialog.move(-3000, -3000)
        help_dialog.show()
        app.processEvents()
        grab(help_dialog, SCREENSHOTS_DIR / "help_dialog.png", app)
        help_dialog.close()

        for key, table_name, card_prefix, file_name in (
            ("dom", "tbl_dom", "card_dom", "main_results_dom.png"),
            ("gorod", "tbl_gorod", "card_gor", "main_results_gorod.png"),
        ):
            golden_path = GOLDEN_DIR / f"{key}_april_2026.json"
            if not golden_path.is_file():
                continue
            result = json.loads(golden_path.read_text(encoding="utf-8"))["result"]
            table = getattr(window, table_name)
            window.populate_table(table, result["preview_rows"])
            for suffix, value in (
                ("day", result["total_day"]),
                ("night", result["total_night"]),
                ("odn", result.get("total_odn", result.get("total_simple", 0.0))),
                ("total", result["total_all"]),
            ):
                card = getattr(window, f"{card_prefix}_{suffix}", None)
                if card is not None:
                    card.value_label.setText(f"{value:,.3f} кВт*ч")
            window.lbl_status.setText(f"✅ Расчет завершен! Папка: {result.get('subfolder_name', '')}")
            window.tabs.setCurrentIndex(0 if key == "dom" else 1)
            app.processEvents()
            grab(window, SCREENSHOTS_DIR / file_name, app)

        window.lbl_status.setText("❌ Ошибка при расчете")
        window.progress_bar.setValue(0)
        app.processEvents()
        grab(window, SCREENSHOTS_DIR / "main_error.png", app)

        window.close()


if __name__ == "__main__":
    main()
