# Full verification pass: Rust crates, Tauri shell, parity tests, UI typecheck/build.
# A fresh git worktree has no node_modules, so UI dependencies are installed first.
# Usage: .\scripts\verify.ps1 [-RequireRustOutput]
# -RequireRustOutput makes style/CF/hyperlink diffs fail instead of xfail.
# Missing Rust output is always a hard failure.
param([switch]$RequireRustOutput)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

$root = Split-Path -Parent $PSScriptRoot
$failed = $false

function Invoke-Step([string]$Name, [scriptblock]$Command) {
    Write-Host "==> $Name"
    # cargo/npm write progress to stderr; PS 5.1 turns that into error records when
    # the script output is piped, so success is decided by the exit code only.
    $ErrorActionPreference = "Continue"
    & $Command
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "FAILED: $Name (exit $code)"
    }
}

Push-Location $root
try {
    if (-not (Test-Path (Join-Path $root "apps\ui\node_modules\typescript\package.json"))) {
        Invoke-Step "npm ci (apps/ui)" { npm --prefix apps/ui ci --no-audit --no-fund }
    }

    # Tauri's generate_context! reads frontendDist at compile time, so build the
    # UI before any src-tauri cargo step in a fresh checkout/worktree.
    Invoke-Step "npm typecheck" { npm --prefix apps/ui run typecheck }
    Invoke-Step "npm build" { npm --prefix apps/ui run build }

    Invoke-Step "cargo test tns-core" { cargo test --manifest-path crates/tns-core/Cargo.toml }
    Invoke-Step "cargo test tns-db" { cargo test --manifest-path crates/tns-db/Cargo.toml }
    Invoke-Step "cargo test tns-excel" { cargo test --manifest-path crates/tns-excel/Cargo.toml }
    Invoke-Step "cargo test src-tauri" { cargo test --manifest-path src-tauri/Cargo.toml }
    Invoke-Step "cargo check src-tauri" { cargo check --manifest-path src-tauri/Cargo.toml }
    Invoke-Step "cargo build tns-parity" { cargo build --manifest-path crates/tns-parity/Cargo.toml }
    $env:TNS_PARITY_BIN = Join-Path $root "target\debug\tns-parity.exe"
    $env:TNS_REQUIRE_RUST_OUTPUT = if ($RequireRustOutput) { "1" } else { "0" }
    Invoke-Step "pytest tests/parity" { python -m pytest tests/parity -q }
    # Fixtures and golden outputs are the oracle contract. Harness code under
    # tests/parity is allowed to evolve (signature coverage, Rust driver).
    # Compare against the remote base, not the checked-out branch: on CI the
    # local branch is the commit under test, so a local base would make the
    # guard a no-op. Workflows fetch origin/parity-harness explicitly.
    $guardBase = "origin/parity-harness"
    if (-not (git rev-parse --verify --quiet $guardBase)) {
        throw "Guard base $guardBase not found; fetch origin/parity-harness first"
    }
    Invoke-Step "legacy/parity guard" { git diff --exit-code $guardBase -- legacy/pyqt tests/parity/fixtures }
}
catch {
    $failed = $true
    Write-Host $_.Exception.Message
}
finally {
    Pop-Location
}

if ($failed) {
    exit 1
}

Write-Host "All checks passed."