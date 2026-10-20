[CmdletBinding()]
param(
    [string]$AfterEffectsExe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-AfterEffectsExecutable {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return [System.IO.Path]::GetFullPath($ExplicitPath)
    }

    $registryRoots = @(
        'HKLM:\SOFTWARE\Adobe\After Effects',
        'HKLM:\SOFTWARE\WOW6432Node\Adobe\After Effects'
    )
    $candidates = @()

    foreach ($registryRoot in $registryRoots) {
        if (-not (Test-Path -LiteralPath $registryRoot)) {
            continue
        }

        foreach ($versionKey in Get-ChildItem -LiteralPath $registryRoot -ErrorAction SilentlyContinue) {
            try {
                $installPath = (Get-ItemProperty -LiteralPath $versionKey.PSPath -Name InstallPath -ErrorAction Stop).InstallPath
                $candidatePath = Join-Path $installPath 'AfterFX.exe'
                if (Test-Path -LiteralPath $candidatePath -PathType Leaf) {
                    $parsedVersion = [version]'0.0'
                    [void][version]::TryParse($versionKey.PSChildName, [ref]$parsedVersion)
                    $candidates += [pscustomobject]@{
                        Version = $parsedVersion
                        Path = [System.IO.Path]::GetFullPath($candidatePath)
                    }
                }
            } catch {
                continue
            }
        }
    }

    $detected = $candidates | Sort-Object Version -Descending | Select-Object -First 1
    if ($detected) {
        return $detected.Path
    }

    throw 'Adobe After Effects was not found in the Windows registry.'
}

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$sourcePath = Join-Path $workspaceRoot 'jsx\Codex Bridge.jsx'
$AfterEffectsExe = Resolve-AfterEffectsExecutable -ExplicitPath $AfterEffectsExe
$supportFilesRoot = Split-Path -Parent $AfterEffectsExe
$panelRoot = Join-Path $supportFilesRoot 'Scripts\ScriptUI Panels'
$destinationPath = Join-Path $panelRoot 'Codex AE Bridge.jsx'

if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Bridge source not found: $sourcePath"
}

if (-not (Test-Path -LiteralPath $panelRoot -PathType Container)) {
    throw "After Effects ScriptUI Panels folder not found: $panelRoot"
}

try {
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
} catch [System.UnauthorizedAccessException] {
    throw (
        "Administrator permission is required to install the panel into Program Files. " +
        "Run this script from an elevated PowerShell window: $PSCommandPath"
    )
}

$sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
$destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
if ($sourceHash -ne $destinationHash) {
    throw 'Installed panel hash does not match the workspace source.'
}

[pscustomobject]@{
    Installed = $true
    AfterEffectsExe = $AfterEffectsExe
    Panel = $destinationPath
    Sha256 = $destinationHash
    NextStep = 'Restart After Effects, then open Window > Codex AE Bridge.'
} | Format-List

