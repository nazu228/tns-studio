# vendored PDFium

- File: `pdfium.dll`
- Version: 153.0.7999.0 (PDFium API tag `153.0.7999.0`, pdfium-binaries build)
- Source: `pypdfium2_raw` 5.13.0 wheel for Windows x64
  (`...\site-packages\pypdfium2_raw\pdfium.dll`, produced by `pdfium-binaries`)
- Size: 7 260 672 bytes
- SHA-256: `fb898a1f5ace57805834f390407500bdb6ef93eff326a252ad334a8aae809d8e`

`licenses/` mirrors the `licenses/` directory shipped in the
`pypdfium2-5.13.0.dist-info` wheel metadata:

- `licenses/LICENSES/` - pypdfium2's own license texts (Apache-2.0,
  BSD-3-Clause, CC-BY-4.0).
- `licenses/data/windows_x64/BUILD_LICENSES/` - licenses of the libraries
  linked into this PDFium build (PDFium/Chromium, ICU, FreeType, libjpeg-turbo,
  libpng, libtiff, OpenJPEG, lcms, zlib, abseil, etc.).

The DLL is committed to the repository for development and tests. Release
packaging is a separate concern and may ship it as a sidecar file.

Runtime lookup order (see `src/pdfium.rs`):

1. `PDFIUM_DYNAMIC_LIB_PATH` (DLL path or directory),
2. directory of the current executable,
3. `CARGO_MANIFEST_DIR/vendor` (development / `cargo test`).

Note: PDFium 153 does not export `FPDF_GetVersion`; the loader treats that
symbol as optional and reports the vendored version when it is absent. All
other symbols listed in the parser are required.
