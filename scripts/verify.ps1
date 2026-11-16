# Full verification pass: Rust crates, Tauri shell, parity tests, UI typecheck/build.
# A fresh git worktree has no node_modules, so UI dependencies are installed first.
# Usage: .\scripts\verify.ps1
$ErrorActionPreference = "Stop"

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

    Invoke-Step "cargo test tns-core" { cargo test --manifest-path crates/tns-core/Cargo.toml }
    Invoke-Step "cargo test tns-db" { cargo test --manifest-path crates/tns-db/Cargo.toml }
    Invoke-Step "cargo test tns-excel" { cargo test --manifest-path crates/tns-excel/Cargo.toml }
    Invoke-Step "cargo check src-tauri" { cargo check --manifest-path src-tauri/Cargo.toml }
    Invoke-Step "pytest tests/parity" { python -m pytest tests/parity -q }
    Invoke-Step "npm typecheck" { npm --prefix apps/ui run typecheck }
    Invoke-Step "npm build" { npm --prefix apps/ui run build }
    Invoke-Step "legacy/parity guard" { git diff --exit-code origin/parity-harness -- legacy/pyqt tests/parity }
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