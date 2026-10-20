[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RunId,

    [switch]$IHaveVerifiedAfterEffectsIsIdle
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$lockPath = Join-Path $workspaceRoot '.ae-codex\active.lock'
$ownerPath = Join-Path $lockPath 'owner.json'

if (-not (Test-Path -LiteralPath $ownerPath -PathType Leaf)) {
    throw "No active lock owner was found at: $ownerPath"
}

$owner = Get-Content -LiteralPath $ownerPath -Raw | ConvertFrom-Json
if ($owner.runId -ne $RunId) {
    throw "Run ID does not match the active lock. Active run ID: $($owner.runId)"
}

$hasTerminalStatus = $false
if (Test-Path -LiteralPath $owner.statusPath -PathType Leaf) {
    try {
        $status = Get-Content -LiteralPath $owner.statusPath -Raw | ConvertFrom-Json
        $hasTerminalStatus = $status.state -in @('success', 'error')
    } catch {
        $hasTerminalStatus = $false
    }
}

if (-not $hasTerminalStatus -and -not $IHaveVerifiedAfterEffectsIsIdle) {
    throw (
        'The run has no terminal status. Verify in After Effects that the JSX is no longer running, ' +
        'then rerun with -IHaveVerifiedAfterEffectsIsIdle.'
    )
}

Remove-Item -LiteralPath $ownerPath -Force
Remove-Item -LiteralPath $lockPath -Force
Write-Host "Cleared After Effects JSX lock for run: $RunId"

