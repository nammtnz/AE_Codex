#Requires -Version 7.0
[CmdletBinding()]
param(
    # Fixture/repair mode updates only an existing owned table, without invoking Codex.
    [switch]$SkipRegistration,
    [string]$ConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$workspaceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$serverPath = Join-Path $PSScriptRoot 'AeFunctionsMcp.js'
if (-not (Test-Path -LiteralPath $serverPath -PathType Leaf)) { throw "AE MCP server is missing: $serverPath" }
if ($ConfigPath -and -not $SkipRegistration) { throw '-ConfigPath is allowed only with -SkipRegistration; normal registration uses the active Codex user configuration.' }
$nodePath = (Get-Command node -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$pwshPath = (Get-Command pwsh -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
if (-not $ConfigPath) {
    $codexUserDirectory = if ([string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
    } else { $env:CODEX_HOME }
    $ConfigPath = Join-Path $codexUserDirectory 'config.toml'
}
$ConfigPath = [IO.Path]::GetFullPath($ConfigPath)
if (-not $SkipRegistration) {
    $codexPath = (Get-Command codex -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $registrationArguments = @('mcp', 'add', 'ae_functions', '--env', "CODEX_AE_PWSH=$pwshPath", '--', $nodePath, $serverPath)
    # Do not echo other configuration or diagnostic text that might contain credentials.
    & $codexPath @registrationArguments 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Codex MCP registration failed with exit code $LASTEXITCODE. Existing project trust settings were not changed." }
}
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw "Codex configuration not found: $ConfigPath" }
$original = [IO.File]::ReadAllText($ConfigPath)
$newline = if ($original.Contains("`r`n")) { "`r`n" } else { "`n" }

# Track TOML multiline strings so a header or assignment inside a prompt is never edited.
$records = [Collections.Generic.List[object]]::new()
$multiline = ''
foreach ($match in [regex]::Matches($original, '[^\r\n]*(?:\r\n|\n|\r|$)')) {
    if (-not $match.Length) { continue }
    $line = $match.Value
    $outside = -not $multiline
    $content = $line.TrimEnd("`r", "`n")
    $header = $outside -and $content -match '^\s*\[.+\]\s*(?:#.*)?$'
    $owned = $header -and $content -match '^\s*\[\s*mcp_servers\s*\.\s*(?:ae_functions|"ae_functions"|''ae_functions'')\s*\]\s*(?:#.*)?$'
    $records.Add([pscustomobject]@{ Text = $line; Outside = $outside; Header = $header; Owned = $owned })
    $index = 0
    while ($index -lt $content.Length) {
        if ($multiline) {
            if ($multiline -eq '"""' -and $content[$index] -eq '\') { $index += 2; continue }
            if ($index + 3 -le $content.Length -and $content.Substring($index, 3) -eq $multiline) { $multiline = ''; $index += 3; continue }
            $index += 1; continue
        }
        $character = $content[$index]
        if ($character -eq '#') { break }
        if ($character -eq '"' -or $character -eq "'") {
            $quote = [string]$character
            if ($index + 3 -le $content.Length -and $content.Substring($index, 3) -eq ($quote * 3)) {
                $multiline = $quote * 3; $index += 3; continue
            }
            $index += 1
            while ($index -lt $content.Length) {
                if ($quote -eq '"' -and $content[$index] -eq '\') { $index += 2; continue }
                if ([string]$content[$index] -eq $quote) { $index += 1; break }
                $index += 1
            }
            continue
        }
        $index += 1
    }
}
if ($multiline) { throw 'Cannot safely edit Codex configuration: an unterminated multiline TOML string was found.' }
$ownedIndices = @()
for ($index = 0; $index -lt $records.Count; $index += 1) { if ($records[$index].Owned) { $ownedIndices += $index } }
if ($ownedIndices.Count -ne 1) { throw 'Expected exactly one [mcp_servers.ae_functions] table after registration; configuration was not rewritten.' }
$tableStart = $ownedIndices[0]
$tableEnd = $records.Count
for ($index = $tableStart + 1; $index -lt $records.Count; $index += 1) {
    if ($records[$index].Header) { $tableEnd = $index; break }
}
$found = @{}
for ($index = $tableStart + 1; $index -lt $tableEnd; $index += 1) {
    if ($records[$index].Outside -and $records[$index].Text -match '^\s*(startup_timeout_sec|tool_timeout_sec)\s*=') {
        $key = $Matches[1]
        if ($found.ContainsKey($key)) { throw "Duplicate owned timeout setting: $key" }
        $found[$key] = $true
        $value = if ($key -eq 'startup_timeout_sec') { 10 } else { 210 }
        $records[$index].Text = "$key = $value$newline"
    }
}
$insert = ''
foreach ($key in @('startup_timeout_sec', 'tool_timeout_sec')) {
    if (-not $found.ContainsKey($key)) {
        $value = if ($key -eq 'startup_timeout_sec') { 10 } else { 210 }
        $insert += "$key = $value$newline"
    }
}
if ($insert) {
    if (-not $records[$tableStart].Text.EndsWith("`n")) { $records[$tableStart].Text += $newline }
    $records[$tableStart].Text += $insert
}
$updated = ($records | ForEach-Object { $_.Text }) -join ''
$changed = $updated -cne $original
if ($changed) {
    $temporaryPath = $ConfigPath + '.ae-functions-' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        # The only temporary full-config copy stays adjacent to the user's config, never in workspace logs.
        [IO.File]::WriteAllText($temporaryPath, $updated, [Text.UTF8Encoding]::new($false))
        if ([IO.File]::ReadAllText($ConfigPath) -cne $original) { throw 'Codex configuration changed concurrently; timeout changes were not published. Run this installer again.' }
        [IO.File]::Move($temporaryPath, $ConfigPath, $true)
    } finally { if (Test-Path -LiteralPath $temporaryPath -PathType Leaf) { Remove-Item -LiteralPath $temporaryPath -Force } }
}
[ordered]@{
    schema = 'codex-ae-mcp-install/v1'; state = 'success'; server = 'ae_functions'
    registered = -not $SkipRegistration; timeoutsUpdated = $changed; configPath = $ConfigPath
    command = $nodePath; serverPath = $serverPath; powershellPath = $pwshPath
    startupTimeoutSeconds = 10; toolTimeoutSeconds = 210
    nextStep = 'Open a new Codex chat or reload the MCP connections to load ae_functions. Project trust settings were not changed.'
} | ConvertTo-Json -Depth 8
