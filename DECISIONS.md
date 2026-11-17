# Decisions

## 2026-11-17 — The xlsx signature is the shared parity oracle

**Context:** the Rust port had result-level golden tests, but no Rust test compared the generated workbook with the legacy golden. The existing `xlsx_signature` also skipped sheet order, conditional-formatting styles, hyperlink details, hidden dimensions, defined names and validations.

**Decision:** extend `tests/parity/parity_lib.py::xlsx_signature` and add `crates/tns-parity` as the Rust driver for pytest. Both the legacy oracle and the Rust output are compared through the same openpyxl signature.

**Why:** the verifier must stay independent from both implementations. Testing Rust output with a Rust extractor would hide shared blind spots.

**Consequence:** `test_rust_result_matches_golden` is enforced now. `test_rust_xlsx_matches_golden` is xfailed while `process_statement` does not write the output workbook; it becomes the acceptance test for that slice. Use `scripts/verify.ps1 -RequireRustOutput` as the release gate once the writer lands.

**Tried and rejected:** `rust_xlsxwriter` cannot modify an existing workbook; Harness² is benchmark-oriented and does not replace the golden oracle.
