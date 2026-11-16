# Run cargo with the MSVC environment (link.exe, Windows SDK libs).
# Usage: .\scripts\cargo.ps1 test --manifest-path crates/tns-core/Cargo.toml
$ErrorActionPreference = "Stop"

$vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "vswhere.exe not found. Install Visual Studio Build Tools with the C++ workload."
}

$install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $install) {
    throw "Visual Studio Build Tools with VCTools not found."
}

$vcvars = Join-Path $install "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvars)) {
    throw "vcvars64.bat not found at $vcvars"
}

$cargo = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
if (-not (Test-Path $cargo)) {
    $cargo = "cargo"
}

$command = "call `"$vcvars`" >nul && `"$cargo`" $($args -join ' ')"
& cmd.exe /c $command
exit $LASTEXITCODE
