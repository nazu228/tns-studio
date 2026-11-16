"""Parity tests: legacy TNS engine vs golden outputs.

These tests are the oracle contract for the Rust port. They do not import or
modify the new Rust code yet; they prove that fixtures and golden files are
reproducible on this machine.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from parity_lib import diff_dicts, normalize_result, run_oracle, sha256_file, xlsx_signature


def test_fixtures_exist(parity_dirs, fixtures_manifest):
    assert fixtures_manifest["fixtures"], "no fixtures in manifest"
    for fixture in fixtures_manifest["fixtures"]:
        path = parity_dirs.fixtures / fixture["file"]
        assert path.is_file(), f"missing fixture: {path}"
        assert fixture["sha256"] == sha256_file(path), f"fixture hash mismatch: {path}"


def test_golden_manifest_hashes(parity_dirs, golden_manifest):
    assert golden_manifest["fixtures"], "no golden fixtures"
    for golden in golden_manifest["fixtures"]:
        path = parity_dirs.golden / golden["golden_xlsx"]
        assert path.is_file(), f"missing golden xlsx: {path}"
        assert golden["sha256"] == sha256_file(path), f"golden hash mismatch: {path}"


@pytest.mark.parametrize("golden_index", range(3))
def test_golden_reproducible(parity_dirs, golden_manifest, golden_index):
    if golden_index >= len(golden_manifest["fixtures"]):
        pytest.skip("not enough golden fixtures")
    golden = golden_manifest["fixtures"][golden_index]
    fixture = parity_dirs.fixtures / golden["fixture"]
    golden_xlsx = parity_dirs.golden / golden["golden_xlsx"]

    with tempfile.TemporaryDirectory(prefix="tns-parity-") as tmp:
        tmp_dir = Path(tmp)
        result, events = run_oracle(fixture, tmp_dir, golden["month"], golden["year"])
        normalized = normalize_result(result, tmp_dir)
        target = Path(result["target_path"])

        diffs = diff_dicts(golden["result"], normalized)
        assert not diffs, "legacy result differs from golden:\n" + "\n".join(diffs[:20])
        assert target.is_file(), f"legacy engine did not create {target}"

        expected_signature = xlsx_signature(golden_xlsx)
        actual_signature = xlsx_signature(target)
        assert actual_signature == expected_signature, (
            "xlsx content differs from golden: "
            f"{golden['golden_xlsx']} vs {target}"
        )
        assert events, "legacy engine must emit progress events"


def test_zone_classification():
    from core_engine import classify_zone

    assert classify_zone("День") == "day"
    assert classify_zone("Т1") == "day"
    assert classify_zone("Ночь") == "night"
    assert classify_zone("Т2") == "night"
    assert classify_zone("ОДН") == "odn"
    assert classify_zone("") == "odn"


def test_numeric_value():
    from tns_input import numeric_value

    assert numeric_value("1 000,00", "AB11") == 1000.0
    assert numeric_value("—", "AB11") == 0.0
    assert numeric_value(None, "AB11") == 0.0
    with pytest.raises(ValueError):
        numeric_value("not-a-number", "AB11")
