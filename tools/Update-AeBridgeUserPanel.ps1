#Requires -Version 7.0
[CmdletBinding()]
param(
    [ValidatePattern('^\d+\.\d+$')]
    [string]$VersionFolder = '26.5'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-AeBridgeUserScriptsPath {
    param([string]$TargetPath, [string]$ScriptsRoot)
    $resolvedRoot = [IO.Path]::GetFullPath($ScriptsRoot).TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $resolvedTarget = [IO.Path]::GetFullPath($TargetPath)
    if (-not $resolvedTarget.StartsWith($resolvedRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Panel or startup path escaped the user Scripts folder.'
    }
    $cursor = $resolvedTarget
    while ($cursor) {
        if ((Test-Path -LiteralPath $cursor) -and
            ([IO.File]::GetAttributes($cursor) -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse point is not allowed: $cursor"
        }
        $parent = [IO.Directory]::GetParent($cursor)
        if ($null -eq $parent) { break }
        $cursor = $parent.FullName
    }
}

function Install-AeBridgeStartupLoader {
    param([string]$ScriptsRoot, [string]$BundlePath, [string]$TemplatePath, [string]$BackupRoot)
    $startupRoot = Join-Path $ScriptsRoot 'Startup'
    $startupPath = [IO.Path]::GetFullPath((Join-Path $startupRoot 'Codex Bridge Startup.jsx'))
    Assert-AeBridgeUserScriptsPath -TargetPath $startupPath -ScriptsRoot $ScriptsRoot
    $utf8 = [Text.UTF8Encoding]::new($false)
    $template = [IO.File]::ReadAllText($TemplatePath, $utf8)
    if ([regex]::Matches($template, '__CODEX_AE_WORKSPACE_BUNDLE__').Count -ne 1) { throw 'Startup template must contain exactly one workspace bundle placeholder.' }
    $bundleLiteral = ConvertTo-Json -InputObject ([IO.Path]::GetFullPath($BundlePath)) -Compress -EscapeHandling EscapeNonAscii
    $content = $template.Replace('__CODEX_AE_WORKSPACE_BUNDLE__', $bundleLiteral)
    $expectedHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($utf8.GetBytes($content)))
    $backupPath = $null
    if ((Test-Path -LiteralPath $startupPath -PathType Leaf) -and
        (Get-FileHash -LiteralPath $startupPath -Algorithm SHA256).Hash -eq $expectedHash) {
        return [pscustomobject]@{path=$startupPath;sha256=$expectedHash;backupPath=$null;updated=$false;workspaceBundle=[IO.Path]::GetFullPath($BundlePath)}
    }
    New-Item -ItemType Directory -Force -Path $startupRoot | Out-Null
    if (Test-Path -LiteralPath $startupPath -PathType Leaf) {
        New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
        $backupPath = Join-Path $BackupRoot ("Codex Bridge Startup-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))-$([guid]::NewGuid().ToString('N').Substring(0,8)).jsx")
        Copy-Item -LiteralPath $startupPath -Destination $backupPath
    }
    $temporaryPath = Join-Path $startupRoot ("Codex Bridge Startup.jsx.tmp-$([guid]::NewGuid().ToString('N'))")
    try {
        [IO.File]::WriteAllText($temporaryPath, $content, $utf8)
        if ((Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'Temporary startup loader hash mismatch.' }
        [IO.File]::Move($temporaryPath, $startupPath, $true)
        if ((Get-FileHash -LiteralPath $startupPath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'Installed startup loader hash mismatch.' }
    } finally {
        if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath }
    }
    [pscustomobject]@{path=$startupPath;sha256=$expectedHash;backupPath=$backupPath;updated=$true;workspaceBundle=[IO.Path]::GetFullPath($BundlePath)}
}

$workspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$sourcePath = Join-Path $workspaceRoot 'jsx/Codex Bridge.jsx'
$userScriptsRoot = [IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath('ApplicationData')) "Adobe/After Effects/$VersionFolder/Scripts"))
$userPanelRoot = Join-Path $userScriptsRoot 'ScriptUI Panels'
$panelPath = [IO.Path]::GetFullPath((Join-Path $userPanelRoot 'Codex Bridge.jsx'))
Assert-AeBridgeUserScriptsPath -TargetPath $panelPath -ScriptsRoot $userScriptsRoot
if (-not (Test-Path -LiteralPath $panelPath -PathType Leaf)) { throw "Existing user panel not found: $panelPath" }
$backupRoot = Join-Path $workspaceRoot '.ae-codex/bridge/backups'
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$backupPath = Join-Path $backupRoot ("Codex Bridge-$([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))-$([guid]::NewGuid().ToString('N').Substring(0,8)).jsx")
Copy-Item -LiteralPath $panelPath -Destination $backupPath
$temporaryPath = Join-Path $userPanelRoot ("Codex Bridge.jsx.tmp-$([guid]::NewGuid().ToString('N'))")
try {
    Copy-Item -LiteralPath $sourcePath -Destination $temporaryPath
    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    if ((Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash -ne $sourceHash) { throw 'Temporary panel hash mismatch.' }
    $validation = & (Join-Path $PSScriptRoot 'Validate-AeBridgeInstallation.ps1') -WorkspaceRoot $workspaceRoot | ConvertFrom-Json
    if ($validation.state -cne 'success' -or $validation.sha256 -ine $sourceHash -or
        (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -ne $sourceHash -or
        (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash -ne $sourceHash) {
        throw 'Workspace or staged panel changed during installation validation. The installed panel was preserved.'
    }
    [IO.File]::Move($temporaryPath, $panelPath, $true)
    if ((Get-FileHash -LiteralPath $panelPath -Algorithm SHA256).Hash -ne $sourceHash) { throw 'Installed panel hash mismatch.' }
} finally { if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath } }
if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash -ne $sourceHash) {
    throw 'Workspace bundle changed after installing the verified panel. Run the updater again before enabling startup.'
}
$startupLoader = Install-AeBridgeStartupLoader -ScriptsRoot $userScriptsRoot -BundlePath $sourcePath -TemplatePath (Join-Path $PSScriptRoot 'AeBridgeStartup.js') -BackupRoot $backupRoot
[pscustomobject]@{
    updated=$true
    panelPath=$panelPath
    backupPath=$backupPath
    sha256=$sourceHash
    validation=$validation
    startupLoader=$startupLoader
    nextStep='Close and reopen Window > Codex Bridge to use the update now. On future After Effects launches the user Startup loader connects automatically; no Start click is needed.'
} | ConvertTo-Json -Depth 4
