<#
.SYNOPSIS
Run the Apple Music bridge; remember credentials using the OS credential store.
#>
[CmdletBinding()]
param(
    [string]$TunnelId = $env:CONTROL_PLANE_TUNNEL_ID,
    [switch]$Doctor,
    [switch]$Check,
    [switch]$Setup
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$client = Join-Path $projectRoot '.bridge\tunnel-client\tunnel-client.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create the project environment first: uv sync --extra dev' }
if ($Check) {
    & $python -m applemusic_mcp bridge --check
    exit $LASTEXITCODE
}
if (-not (Test-Path -LiteralPath $client)) { throw 'Run .\scripts\install-bridge.ps1 first.' }
$bridgeArgs = @('-m', 'applemusic_mcp', 'bridge', '--client', $client, '--interactive', '--remember')
if ($TunnelId) { $bridgeArgs += @('--tunnel-id', $TunnelId) }
if ($Doctor) { $bridgeArgs += '--doctor' }
if ($Setup) { $bridgeArgs += '--setup' }
& $python @bridgeArgs
exit $LASTEXITCODE
