"""Parity checks for the Rust port.

The legacy engine remains the oracle, but both implementations are compared
through the same openpyxl signature (`parity_lib.xlsx_signature`). The Rust
driver is `crates/tns-parity`; it is built by `scripts/verify.ps1` or found at
`target/debug/tns-parity[.exe]`. Set `TNS_PARITY_BIN` to use an explicit binary.

Result parity is enforced now. Workbook parity is the acceptance test for the
output-writing slice: while `process_statement` does not create the target
file, the xlsx test is xfailed with a clear reason. Once the writer lands it
becomes a normal assertion. Set `TNS_REQUIRE_RUST_OUTPUT=1` to turn a missing
workbook into a hard failure (used by the release gate).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from parity_lib import diff_dicts, normalize_result, xlsx_signature


def _rust_command(parity_dirs) -> list[str]:
    configured = os.environ.get("TNS_PARITY_BIN")
    if configured:
        binary = Path(configured)
        assert binary.is_file(), f"TNS_PARITY_BIN does not exist: {binary}"
        return [str(binary)]

    for name in ("tns-parity.exe", "tns-parity"):
        binary = parity_dirs.root / "target" / "debug" / name
        if binary.is_file():
            return [str(binary)]

    return [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(parity_dirs.root / "Cargo.toml"),
        "-p",
        "tns-parity",
        "--",
    ]


def _run_rust(parity_dirs, fixture: Path, month: str, year: str, tmp_path: Path):
    output_dir = tmp_path / "out"
    result_path = tmp_path / "rust-result.json"
    command = (
        _rust_command(parity_dirs)
        + [
            "--fixture",
            str(fixture),
            "--output-dir",
            str(output_dir),
            "--month",
            month,
            "--year",
            year,
            "--result",
            str(result_path),
        ]
    )
    completed = subprocess.run(
        command,
        cwd=parity_dirs.root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if completed.returncode != 0:
        pytest.fail(
            "tns-parity failed with exit code "
            f"{completed.returncode}\ncommand: {command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not result_path.is_file():
        pytest.fail(f"tns-parity did not write {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return result, output_dir


@pytest.mark.parametrize("golden_index", range(3))
def test_rust_result_matches_golden(parity_dirs, golden_manifest, golden_index, tmp_path):
    if golden_index >= len(golden_manifest["fixtures"]):
        pytest.skip("not enough golden fixtures")
    golden = golden_manifest["fixtures"][golden_index]
    fixture = parity_dirs.fixtures / golden["fixture"]

    result, output_dir = _run_rust(
        parity_dirs, fixture, golden["month"], golden["year"], tmp_path
    )
    normalized = normalize_result(result, output_dir)
    diffs = diff_dicts(golden["result"], normalized)
    assert not diffs, "Rust result differs from golden:\n" + "\n".join(diffs[:40])


@pytest.mark.parametrize("golden_index", range(3))
def test_rust_xlsx_matches_golden(parity_dirs, golden_manifest, golden_index, tmp_path):
    if golden_index >= len(golden_manifest["fixtures"]):
        pytest.skip("not enough golden fixtures")
    golden = golden_manifest["fixtures"][golden_index]
    fixture = parity_dirs.fixtures / golden["fixture"]

    result, _ = _run_rust(parity_dirs, fixture, golden["month"], golden["year"], tmp_path)
    target = Path(result["target_path"])
    if not target.is_file():
        message = (
            "Rust process_statement did not write the output workbook: "
            f"{target}. This is the acceptance test for the output-writing slice."
        )
        if os.environ.get("TNS_REQUIRE_RUST_OUTPUT") == "1":
            pytest.fail(message)
        pytest.xfail(message)

    expected_signature = xlsx_signature(parity_dirs.golden / golden["golden_xlsx"])
    actual_signature = xlsx_signature(target)
    diffs = diff_dicts(expected_signature, actual_signature)
    assert not diffs, (
        "Rust xlsx differs from golden signature: "
        f"{golden['golden_xlsx']} vs {target}\n" + "\n".join(diffs[:40])
    )
