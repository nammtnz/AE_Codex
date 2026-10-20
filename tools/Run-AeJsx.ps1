[CmdletBinding(DefaultParameterSetName = 'Script')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Script')]
    [string]$Script,

    [Parameter(Mandatory = $true, ParameterSetName = 'Branch')]
    [string]$Branch,

    [string]$AfterEffectsExe,

    [ValidateRange(5, 900)]
    [int]$TimeoutSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertTo-JavaScriptStringLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)

    return ($Value | ConvertTo-Json -Compress)
}

function Test-IsPathInside {
    param(
        [Parameter(Mandatory = $true)][string]$ParentPath,
        [Parameter(Mandatory = $true)][string]$ChildPath
    )

    $relative = [System.IO.Path]::GetRelativePath($ParentPath, $ChildPath)
    return -not (
        [System.IO.Path]::IsPathRooted($relative) -or
        $relative -eq '..' -or
        $relative.StartsWith("..$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::Ordinal)
    )
}

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

    return 'C:\Program Files\Adobe\Adobe After Effects 2026\Support Files\AfterFX.exe'
}

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$jsxRoot = [System.IO.Path]::GetFullPath((Join-Path $workspaceRoot 'jsx'))
$AfterEffectsExe = Resolve-AfterEffectsExecutable -ExplicitPath $AfterEffectsExe

if (-not (Test-Path -LiteralPath $AfterEffectsExe -PathType Leaf)) {
    throw "After Effects executable not found: $AfterEffectsExe"
}

. (Join-Path $PSScriptRoot 'Resolve-AeScriptTarget.ps1')
$scriptTarget = Resolve-AeScriptTarget -WorkspaceRoot $workspaceRoot -Script $Script -Branch $Branch
$scriptPath = $scriptTarget.Path
if ([System.IO.Path]::GetExtension($scriptPath) -ne '.jsx') {
    throw 'Only .jsx scripts are accepted.'
}

if (-not (Test-IsPathInside -ParentPath $jsxRoot -ChildPath $scriptPath)) {
    throw "For safety, scripts must be inside: $jsxRoot"
}

$bridgeRoot = Join-Path $workspaceRoot '.ae-codex'
$runtimeRoot = Join-Path $bridgeRoot 'runtime'
$resultRoot = Join-Path $bridgeRoot 'results'
New-Item -ItemType Directory -Force -Path $runtimeRoot, $resultRoot | Out-Null

$fileBridgeLock = Join-Path $bridgeRoot 'bridge\submit.lock'
if (Test-Path -LiteralPath $fileBridgeLock -PathType Container) {
    throw "The file bridge has an active or unknown run: $fileBridgeLock"
}

$runId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8))
$runnerPath = Join-Path $runtimeRoot ("runner-$runId.jsx")
$statusPath = Join-Path $resultRoot ("status-$runId.json")
$lockPath = Join-Path $bridgeRoot 'active.lock'
$lockOwnerPath = Join-Path $lockPath 'owner.json'

try {
    New-Item -ItemType Directory -Path $lockPath -ErrorAction Stop | Out-Null
} catch {
    $ownerDescription = 'Owner information is unavailable.'
    if (Test-Path -LiteralPath $lockOwnerPath -PathType Leaf) {
        $ownerDescription = Get-Content -LiteralPath $lockOwnerPath -Raw
    }
    throw "Another After Effects JSX run may still be active. Lock: $lockPath`n$ownerDescription"
}

$lockOwned = $true
$dispatched = $false
$terminalStateObserved = $false

$owner = [ordered]@{
    schema = 'codex-ae-lock/v1'
    runId = $runId
    runnerPid = $PID
    script = $scriptPath
    statusPath = $statusPath
    createdAtUtc = [DateTime]::UtcNow.ToString('o')
}

try {
    $owner | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $lockOwnerPath -Encoding utf8NoBOM

    $targetLiteral = ConvertTo-JavaScriptStringLiteral -Value $scriptPath
    $statusLiteral = ConvertTo-JavaScriptStringLiteral -Value $statusPath
    $runIdLiteral = ConvertTo-JavaScriptStringLiteral -Value $runId
    $bundleLiteral = ConvertTo-JavaScriptStringLiteral -Value (Join-Path $jsxRoot 'Codex Bridge.jsx')
    $branchLiteral = ConvertTo-JavaScriptStringLiteral -Value $scriptTarget.Name
    $bundledLiteral = if ($scriptTarget.Bundled) { 'true' } else { 'false' }

    $runnerSource = @"
(function () {
    var targetPath = $targetLiteral;
    var statusPath = $statusLiteral;
    var runId = $runIdLiteral;

    function pad(value) {
        return value < 10 ? "0" + value : String(value);
    }

    function isoNow() {
        var date = new Date();
        return date.getUTCFullYear() + "-" +
            pad(date.getUTCMonth() + 1) + "-" +
            pad(date.getUTCDate()) + "T" +
            pad(date.getUTCHours()) + ":" +
            pad(date.getUTCMinutes()) + ":" +
            pad(date.getUTCSeconds()) + "Z";
    }

    function jsonEscape(value) {
        return String(value)
            .replace(/\\/g, "\\\\")
            .replace(/\"/g, "\\\"")
            .replace(/\r/g, "\\r")
            .replace(/\n/g, "\\n")
            .replace(/\t/g, "\\t");
    }

    function writeStatus(state, message, result) {
        var statusFile = new File(statusPath);
        var temporaryFile = new File(statusPath + ".tmp");
        var payload = "{" +
            "\"state\":\"" + jsonEscape(state) + "\"," +
            "\"runId\":\"" + jsonEscape(runId) + "\"," +
            "\"script\":\"" + jsonEscape(targetPath) + "\"," +
            "\"afterEffectsVersion\":\"" + jsonEscape(app.version) + "\"," +
            "\"timestamp\":\"" + jsonEscape(isoNow()) + "\"," +
            "\"message\":\"" + jsonEscape(message || "") + "\"," +
            "\"result\":\"" + jsonEscape(result || "") + "\"" +
            "}";

        if (temporaryFile.exists) {
            temporaryFile.remove();
        }

        temporaryFile.encoding = "UTF-8";
        if (!temporaryFile.open("w")) {
            throw new Error("Cannot open temporary status file: " + temporaryFile.error);
        }

        temporaryFile.write(payload);
        temporaryFile.close();

        if (statusFile.exists && !statusFile.remove()) {
            throw new Error("Cannot replace status file: " + statusFile.error);
        }

        if (!temporaryFile.rename(statusFile.name)) {
            throw new Error("Cannot publish status file: " + temporaryFile.error);
        }
    }

    function describeError(error) {
        var description = error && error.toString ? error.toString() : String(error);
        if (error && error.line) {
            description += " (line " + error.line + ")";
        }
        if (error && error.fileName) {
            description += " in " + error.fileName;
        }
        return description;
    }

    try {
        writeStatus("running", "JSX started", "");

        var targetFile = new File(targetPath);
        if (!$bundledLiteral && !targetFile.exists) {
            throw new Error("Target JSX does not exist: " + targetPath);
        }

        var evaluationResult;
        if ($bundledLiteral) {
            try {
                $.global.__CODEX_AE_BUNDLE_ONLY__ = true;
                $.evalFile(new File($bundleLiteral));
            } finally { delete $.global.__CODEX_AE_BUNDLE_ONLY__; }
            evaluationResult = $.global.__codexAeBundleV1.run($branchLiteral);
        } else { evaluationResult = $.evalFile(targetFile); }
        writeStatus(
            "success",
            "JSX completed",
            typeof evaluationResult === "undefined" ? "" : String(evaluationResult)
        );
    } catch (error) {
        try {
            writeStatus("error", describeError(error), "");
        } catch (statusError) {
            // When file access is disabled, After Effects cannot report through
            // the bridge. The PowerShell timeout will explain the likely cause.
        }
    }
}());
"@

    Set-Content -LiteralPath $runnerPath -Value $runnerSource -Encoding utf8NoBOM

    $quotedRunnerPath = '"' + $runnerPath + '"'
    Start-Process -FilePath $AfterEffectsExe -ArgumentList @('-r', $quotedRunnerPath) | Out-Null
    $dispatched = $true

    Write-Host "Run ID: $runId"
    Write-Host "After Effects: $AfterEffectsExe"
    Write-Host "Waiting for After Effects: $statusPath"

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $lastState = $null

    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
            try {
                $status = Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
                $lastState = $status.state

                if ($status.state -eq 'success') {
                    $terminalStateObserved = $true
                    $status | ConvertTo-Json -Depth 5
                    return
                }

                if ($status.state -eq 'error') {
                    $terminalStateObserved = $true
                    throw "After Effects JSX failed: $($status.message)"
                }
            } catch [System.ArgumentException] {
                # A status file should be atomic; retry briefly if a scanner or
                # sync tool exposed it during replacement.
            }
        }

        Start-Sleep -Milliseconds 250
    }

    $stateHint = if ($lastState) { " Last state: $lastState." } else { '' }
    throw (
        "Timed out after $TimeoutSeconds seconds waiting for After Effects.$stateHint " +
        'Check for a modal dialog, then enable Edit > Preferences > Scripting & Expressions > ' +
        "Allow Scripts to Write Files and Access Network. The lock was retained: $lockPath"
    )
} finally {
    if ($lockOwned -and ((-not $dispatched) -or $terminalStateObserved)) {
        if (Test-Path -LiteralPath $lockOwnerPath -PathType Leaf) {
            Remove-Item -LiteralPath $lockOwnerPath -Force
        }
        if (Test-Path -LiteralPath $lockPath -PathType Container) {
            Remove-Item -LiteralPath $lockPath -Force
        }
    } elseif ($lockOwned) {
        Write-Warning "After Effects completion is unknown. Lock retained at: $lockPath"
    }
}
