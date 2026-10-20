#Requires -Version 7.0
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $workspace 'tools/Resolve-AeScriptTarget.ps1')
$target = Resolve-AeScriptTarget -WorkspaceRoot $workspace -Branch hello
if (-not $target.Bundled -or $target.RelativePath -ne 'jsx/hello.jsx') { throw 'Branch resolver failed.' }
$target = Resolve-AeScriptTarget -WorkspaceRoot $workspace -Script (Join-Path $workspace 'jsx/hello.jsx')
if (-not $target.Bundled) { throw 'Legacy script path did not resolve to a branch.' }
$target = Resolve-AeScriptTarget -WorkspaceRoot $workspace -Branch 'HELLO.JSX'
if ($target.Name -cne 'hello.jsx') { throw 'Case-insensitive branch resolution failed.' }
foreach ($branch in @('../hello', 'folder/hello', 'missing-script', 'C:/temp/hello.jsx')) {
    $rejected = $false
    try { Resolve-AeScriptTarget -WorkspaceRoot $workspace -Branch $branch | Out-Null } catch { $rejected = $true }
    if (-not $rejected) { throw "Invalid or missing branch was accepted: $branch" }
}
$rejected = $false
try { Resolve-AeScriptTarget -WorkspaceRoot $workspace -Script (Join-Path $workspace 'source/hello.jsx') | Out-Null } catch { $rejected = $true }
if (-not $rejected) { throw 'Path outside jsx/ was accepted.' }
'PASS branch, legacy path, casing, missing names and path traversal checks'
