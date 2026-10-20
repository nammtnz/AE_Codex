[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$workspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$libraryRoot = Join-Path $workspaceRoot '.ae-codex/library'
New-Item -ItemType Directory -Force -Path $libraryRoot | Out-Null
$powerShellPath = (Get-Process -Id $PID).Path
if ([IO.Path]::GetFileName($powerShellPath) -ne 'pwsh.exe') {
    throw 'Run this initializer with PowerShell 7 (pwsh).'
}
$runtime = [ordered]@{schemaVersion=1;powerShellPath=$powerShellPath}
$runtimePath = Join-Path $libraryRoot 'runtime.json'
$tempPath = "$runtimePath.tmp-$([guid]::NewGuid().ToString('N'))"
try {
    [IO.File]::WriteAllText($tempPath, ($runtime | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($tempPath, $runtimePath, $true)
} finally { if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath } }
& (Join-Path $PSScriptRoot 'Update-AeSfxCatalog.ps1')
