param(
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$AssetPath,
    [Parameter(Mandatory = $true)][string]$SignaturePath,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$Notes = ""
)

$ErrorActionPreference = "Stop"

$Version = $Version.TrimStart("v")
$asset = (Resolve-Path -LiteralPath $AssetPath).Path
$signatureFile = (Resolve-Path -LiteralPath $SignaturePath).Path
$signature = (Get-Content -LiteralPath $signatureFile -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($signature)) {
    throw "Updater signature is empty: $signatureFile"
}
if ([string]::IsNullOrWhiteSpace($Notes)) {
    $Notes = "TNS Energy Studio $Version"
}

$assetName = [IO.Path]::GetFileName($asset)
$assetUrl = "https://github.com/nazu228/tns-studio/releases/download/$Tag/$([Uri]::EscapeDataString($assetName))"
$payload = [ordered]@{
    version   = $Version
    notes     = $Notes
    pub_date  = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    platforms = [ordered]@{
        "windows-x86_64" = [ordered]@{
            signature = $signature
            url       = $assetUrl
        }
    }
}

$json = $payload | ConvertTo-Json -Depth 6
$output = [IO.Path]::GetFullPath($OutputPath)
$parent = Split-Path -Parent $output
if ($parent) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
}
[IO.File]::WriteAllText($output, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote $output"
