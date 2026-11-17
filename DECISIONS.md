# Decisions

## 2026-11-17 — The xlsx signature is the shared parity oracle

**Context:** the Rust port had result-level golden tests, but no Rust test compared the generated workbook with the legacy golden. The existing `xlsx_signature` also skipped sheet order, conditional-formatting styles, hyperlink details, hidden dimensions, defined names and validations.

**Decision:** extend `tests/parity/parity_lib.py::xlsx_signature` and add `crates/tns-parity` as the Rust driver for pytest. Both the legacy oracle and the Rust output are compared through the same openpyxl signature.

**Why:** the verifier must stay independent from both implementations. Testing Rust output with a Rust extractor would hide shared blind spots.

**Consequence:** `test_rust_result_matches_golden` is enforced now. `test_rust_xlsx_matches_golden` became the acceptance test for the writer; after slice 2 it passes on all three fixtures. Use `scripts/verify.ps1 -RequireRustOutput` as the release gate.

**Tried and rejected:** `rust_xlsxwriter` cannot modify an existing workbook; Harness² is benchmark-oriented and does not replace the golden oracle.

## 2026-11-17 — Slice 1 gates the workbook through the layout signature

**Context:** `process_statement` now writes the output workbook, but the full xlsx signature still differs by styles, number formats, conditional formatting and hyperlinks. Those are deliberately deferred to slice 2.

**Decision:** `xlsx_signature(path, include_styles=False)` is the enforced slice-1 gate. It compares sheet order, values/formulas, merges, freeze panes, dimensions, validations and defined names against the golden, while the full signature remains the release gate (`scripts/verify.ps1 -RequireRustOutput`).

**Why:** the slice can be verified with the independent openpyxl oracle without accepting style regressions or weakening the full gate.

**Consequence:** missing Rust output is a hard failure for both xlsx tests after slice 1. The full test xfailed only on style/CF/hyperlink diffs until slice 2; since slice 2 it passes and `TNS_REQUIRE_RUST_OUTPUT=1` hard-fails any future presentation diff.

**Tried and rejected:** xfail on missing output after the writer landed (it would hide a writer regression); comparing Rust output with a Rust extractor (shared blind spots).

## 2026-11-17 — umya coalesces equal adjacent column widths

**Context:** umya-spreadsheet 3.1.1 writes one `<col min=".." max="..">` range for adjacent columns with the same width. openpyxl exposes such a range as a single dimension, while the legacy openpyxl output has one entry per column.

**Decision:** `output.rs::set_column_widths` nudges the second equal adjacent width by `1e-7`; the signature rounds widths to 6 decimals, so it still reads 18/22/24.

**Why:** it keeps per-column dimensions visible to the oracle without a custom xlsx post-processor.

**Consequence:** actual XML widths are e.g. `22.0000001`; visually negligible, but not byte-exact. Revisit when umya writes one `<col>` per column or when a post-processor becomes worthwhile.

**Tried and rejected:** relying on the merged range (oracle sees fewer columns); changing the oracle rounding to hide the difference.

## 2026-11-17 — Output writer assumes the statement is sheet 0

**Context:** legacy reads `wb.active`; the Rust parser/writer currently uses `book.sheet(0)`. Golden fixtures are single-sheet, so slice 1 passes. Multi-sheet active-sheet input would read the wrong sheet.

**Decision:** keep single-sheet support for slice 1 and document it. Summary insertion uses `rotate_right(1)` so appended extra sheets keep their order and the summary stays first.

**Why:** multi-sheet statements are outside the golden fixture set; changing the parser API to carry the active index is a separate, testable fix.

**Consequence:** multi-sheet input with a non-zero active sheet is not supported yet; it may fail early or read the cover sheet. Add an active-sheet test before enabling it.

**Tried and rejected:** `swap(0, 1)` for the summary (broke extra-sheet order when more than two sheets).

## 2026-11-17 — Full xlsx signature is now the release gate

**Context:** slice 2 ported fonts, fills, borders, number formats, conditional formatting and hyperlinks. The full `xlsx_signature` now matches the golden on dom/gorod/march, and pytest is 22 passed / 0 xfailed with and without `TNS_REQUIRE_RUST_OUTPUT=1`.

**Decision:** the full signature is the release gate. `scripts/verify.ps1 -RequireRustOutput` must be green before merge/release; the layout signature remains a faster regression signal.

**Why:** the workbook is a user-facing deliverable; layout parity alone would accept visible style regressions.

**Consequence:** any style/CF/hyperlink or output regression fails the gate. Missing output is always a hard failure even without the flag.

**Tried and rejected:** keeping the full test xfailed after styles landed; relying only on layout parity.

## 2026-11-17 — Narrow umya xlsx presentation sanitizers

**Context:** umya-spreadsheet 3.1.1 always writes `<diagonal/>` for a border, even when the diagonal is empty, and writes an empty styled cell as numeric rather than `inlineStr`. openpyxl reports `diagonal: Side(None, None)` instead of `None`, and `t: n` instead of `t: inlineStr`, so the full golden signature differs even though the visible workbook is correct.

**Decision:** `tns-excel` post-processes only `xl/styles.xml` (remove `<diagonal/>`/`<diagonal />` from borders that have at least one styled side) and the specified empty summary cell (add `t="inlineStr"`). `process_statement` passes only `A{6 + houses.len()}` on the summary sheet. All other XML, values, styles and non-empty diagonals are preserved.

**Why:** the changes are semantic no-ops for Excel but make the independent oracle compare like for like, without weakening `tests/parity` or special-casing the oracle.

**Consequence:** every `tns-excel::write` rewrites the zip styles.xml; tests cover empty/non-empty diagonals and the inline-string marker. The behavior is tied to umya 3.1.1 and should be revisited when the writer stops emitting the empty diagonal or supports inline strings.

**Tried and rejected:** changing `xlsx_signature` to ignore diagonals/inlineStr (weakens the oracle); accepting an xfail after slice 2; manipulating `origin/parity-harness` to make the guard pass (not a verification method).
