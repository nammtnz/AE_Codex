[CmdletBinding()]
param(
    [ValidateSet('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-luna')]
    [string]$Model,
    [switch]$List,
    [switch]$Preview
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$models = @('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-luna')
$configRoot = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
    Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
} else {
    $env:CODEX_HOME
}
$configPath = Join-Path $configRoot 'config.toml'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Codex config was not found: $configPath"
}
if (((Get-Item -LiteralPath $configPath).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Refusing to modify a config file that is a symbolic link.'
}

$original = [IO.File]::ReadAllText($configPath)
# Only inspect the root TOML section; model keys in profiles/providers are separate.
$firstSection = [regex]::Match($original, '(?m)^\s*\[')
$rootLength = if ($firstSection.Success) { $firstSection.Index } else { $original.Length }
$rootText = $original.Substring(0, $rootLength)
$tailText = $original.Substring($rootLength)
$modelPattern = '(?m)^model\s*=\s*"([^"\r\n]+)"[^\r\n]*'
$matchesFound = [regex]::Matches($rootText, $modelPattern)
if ($matchesFound.Count -gt 1) { throw 'Multiple root model keys found; fix config before switching.' }
$current = if ($matchesFound.Count -eq 1) { $matchesFound[0].Groups[1].Value } else { '(app default)' }

Write-Host "Current model: $current"
if ($List) {
    $models
    Write-Host 'Availability depends on your provider. This list does not query the proxy.'
    return
}
if ([string]::IsNullOrWhiteSpace($Model)) {
    for ($index = 0; $index -lt $models.Count; $index += 1) {
        Write-Host ('{0}. {1}' -f ($index + 1), $models[$index])
    }
    $choice = Read-Host 'Choose a number (Enter to cancel)'
    if ([string]::IsNullOrWhiteSpace($choice)) { return }
    $choiceNumber = 0
    if (-not [int]::TryParse($choice, [ref]$choiceNumber) -or
        $choiceNumber -lt 1 -or $choiceNumber -gt $models.Count) {
        throw 'Invalid model selection. Config was not changed.'
    }
    $Model = $models[$choiceNumber - 1]
}

if ($Preview) {
    [pscustomobject]@{ Config = $configPath; CurrentModel = $current; SelectedModel = $Model; Changed = $false }
    return
}
if ($current -eq $Model) {
    & (Join-Path $PSScriptRoot 'Sync-CodexModelDisplay.ps1')
    Write-Host "Already configured: $Model. No change needed."
    return
}
$newLine = if ($original.Contains("`r`n")) { "`r`n" } else { "`n" }
$newModelLine = 'model = "' + $Model + '"'
$updatedRoot = if ($matchesFound.Count -eq 1) {
    [regex]::Replace($rootText, $modelPattern, $newModelLine)
} else {
    $newModelLine + $newLine + $rootText
}
$updated = $updatedRoot + $tailText
# Detect edits by another application before publishing.
if ([IO.File]::ReadAllText($configPath) -cne $original) {
    throw 'Config changed during selection. Try again with the latest config.'
}
$temporary = $configPath + '.model-switch-' + [guid]::NewGuid().ToString('N') + '.tmp'
try {
    [IO.File]::WriteAllText($temporary, $updated, [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temporary, $configPath, $true)
} finally {
    if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
}
Write-Host "Selected model: $Model"
& (Join-Path $PSScriptRoot 'Sync-CodexModelDisplay.ps1')
Write-Host 'Open a new Codex chat or restart Codex to load the default. Existing chats can keep their own model.'
Write-Host 'This changes the chat default; automatic approval reviewer model is managed separately.'
