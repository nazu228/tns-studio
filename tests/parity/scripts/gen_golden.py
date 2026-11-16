#!/usr/bin/env python3
"""Generate golden outputs from the legacy TNS engine.

The legacy Python engine is the oracle. For every fixture this script runs
legacy process_statement, copies the resulting xlsx into fixtures/golden/ and
stores the normalized result JSON. Tests then compare the Rust port against
these files.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

PARITY_DIR = Path(os.environ.get("TNS_PARITY_DIR") or Path(__file__).resolve().parents[1]).resolve()
ROOT_DIR = PARITY_DIR.parents[1]
LEGACY_DIR = Path(os.environ.get("TNS_LEGACY_DIR") or (ROOT_DIR / "legacy" / "pyqt")).resolve()
FIXTURES_DIR = PARITY_DIR / "fixtures"
GOLDEN_DIR = FIXTURES_DIR / "golden"

sys.path.insert(0, str(LEGACY_DIR))
sys.path.insert(0, str(PARITY_DIR))

from parity_lib import normalize_result, run_oracle, sha256_file  # noqa: E402


def main() -> None:
    manifest_path = FIXTURES_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"fixtures manifest missing: {manifest_path}; run gen_fixtures.py first")
    fixtures = json.loads(manifest_path.read_text(encoding="utf-8"))["fixtures"]
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    golden_manifest = {"generator": "scripts/gen_golden.py", "fixtures": []}
    for fixture in fixtures:
        source = FIXTURES_DIR / fixture["file"]
        with tempfile.TemporaryDirectory(prefix="tns-golden-") as tmp:
            tmp_dir = Path(tmp)
            result, events = run_oracle(source, tmp_dir, fixture["month"], fixture["year"])
            normalized = normalize_result(result, tmp_dir)
            target = Path(result["target_path"])
            if not target.is_file():
                raise SystemExit(f"legacy engine did not create output for {source}: {target}")

            stem = source.stem
            golden_xlsx = GOLDEN_DIR / f"{stem}.xlsx"
            golden_json = GOLDEN_DIR / f"{stem}.json"
            shutil.copyfile(target, golden_xlsx)
            golden_json.write_text(
                json.dumps(
                    {
                        "fixture": fixture["file"],
                        "month": fixture["month"],
                        "year": fixture["year"],
                        "events": events,
                        "result": normalized,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            golden_manifest["fixtures"].append({
                "fixture": fixture["file"],
                "month": fixture["month"],
                "year": fixture["year"],
                "golden_xlsx": golden_xlsx.name,
                "golden_json": golden_json.name,
                "sha256": sha256_file(golden_xlsx),
                "result": normalized,
            })
            print(f"{fixture['file']}: golden={golden_xlsx.name} events={len(events)}")

    (GOLDEN_DIR / "manifest.json").write_text(
        json.dumps(golden_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"golden written to {GOLDEN_DIR}")


if __name__ == "__main__":
    main()
