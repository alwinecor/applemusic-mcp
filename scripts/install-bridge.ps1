<#
.SYNOPSIS
Install the official OpenAI tunnel-client in this checkout, verifying SHA-256.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$architecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
$release = Invoke-RestMethod 'https://api.github.com/repos/openai/tunnel-client/releases/latest'
$assetName = "tunnel-client-$($release.tag_name)-windows-$architecture.zip"
$asset = $release.assets | Where-Object name -eq $assetName
$checksumAsset = $release.assets | Where-Object name -eq 'SHA256SUMS.txt'
if (-not $asset -or -not $checksumAsset) { throw 'Official release is missing the Windows archive or checksums.' }
$downloadDir = Join-Path $projectRoot '.bridge\downloads'
$installDir = Join-Path $projectRoot '.bridge\tunnel-client'
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
$archive = Join-Path $downloadDir $assetName
$checksumFile = Join-Path $downloadDir 'SHA256SUMS.txt'
Invoke-WebRequest $asset.browser_download_url -OutFile $archive
Invoke-WebRequest $checksumAsset.browser_download_url -OutFile $checksumFile
$checksumLines = @(Get-Content -LiteralPath $checksumFile | Where-Object { $_ -match ([regex]::Escape($assetName) + '$') })
if ($checksumLines.Count -ne 1) { throw 'Missing or ambiguous checksum.' }
$expected = ($checksumLines[0] -split '\s+')[0]
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expected) {
    throw 'SHA-256 mismatch; refusing to install.'
}
Expand-Archive -LiteralPath $archive -DestinationPath $installDir -Force
& (Join-Path $installDir 'tunnel-client.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Installed tunnel-client did not start.' }
Write-Host "Installed in $installDir. Next: .\scripts\start-bridge.ps1"
