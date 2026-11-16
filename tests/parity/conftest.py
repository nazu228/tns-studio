"""Pytest configuration for the TNS parity harness.

legacy/pyqt is the read-only oracle. The harness lives in tests/parity and
never writes into the legacy tree.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PARITY_DIR = Path(os.environ.get("TNS_PARITY_DIR") or Path(__file__).resolve().parent).resolve()
ROOT_DIR = PARITY_DIR.parents[1]
LEGACY_DIR = Path(os.environ.get("TNS_LEGACY_DIR") or (ROOT_DIR / "legacy" / "pyqt")).resolve()

FIXTURES_DIR = PARITY_DIR / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"
SCREENSHOTS_DIR = PARITY_DIR / "screenshots"
BENCHMARKS_DIR = PARITY_DIR / "benchmarks"
SCRIPTS_DIR = PARITY_DIR / "scripts"

# Qt must be configured before any PySide6 import. Screenshot tests use the
# offscreen platform; TEST_MODE disables the final QMessageBox in legacy UI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTEST_QT_API", "pyside6")
os.environ.setdefault("TEST_MODE", "1")

sys.path.insert(0, str(LEGACY_DIR))
sys.path.insert(0, str(PARITY_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402


class ParityDirs:
    def __init__(self):
        self.root = ROOT_DIR
        self.parity = PARITY_DIR
        self.legacy = LEGACY_DIR
        self.fixtures = FIXTURES_DIR
        self.golden = GOLDEN_DIR
        self.screenshots = SCREENSHOTS_DIR
        self.benchmarks = BENCHMARKS_DIR
        self.scripts = SCRIPTS_DIR


@pytest.fixture(scope="session")
def parity_dirs():
    if not (LEGACY_DIR / "core_engine.py").is_file() or not (LEGACY_DIR / "tns_input.py").is_file():
        pytest.fail(f"legacy/pyqt not found at {LEGACY_DIR}; set TNS_LEGACY_DIR")
    return ParityDirs()


@pytest.fixture(scope="session")
def fixtures_manifest(parity_dirs):
    path = parity_dirs.fixtures / "manifest.json"
    assert path.is_file(), f"fixtures missing: {path}; run python tests/parity/scripts/gen_fixtures.py"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def golden_manifest(parity_dirs):
    path = parity_dirs.golden / "manifest.json"
    assert path.is_file(), f"golden missing: {path}; run python tests/parity/scripts/gen_golden.py"
    return json.loads(path.read_text(encoding="utf-8"))
