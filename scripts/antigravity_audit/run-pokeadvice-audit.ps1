[CmdletBinding()]
param(
    [string]$AuditWorktree = 'C:\Users\jsp33\Documents\Codex\2026-06-26\github-repo-josun1392-my-pochamps-advisor\work\my_pochamps_advisor-gemini-audit',
    [string]$ProductionWorktree = 'C:\Users\jsp33\Documents\Codex\2026-06-26\github-repo-josun1392-my-pochamps-advisor\work\my_pochamps_advisor',
    [string]$ExpectedHead = 'cdf3a6a71c7a1596108e61ebebf96ca3d3492687',
    [string]$PromptPath = (Join-Path $PSScriptRoot 'prompts\static-correctness-audit.txt'),
    [string]$OutputRoot = (Join-Path $env:USERPROFILE 'agy-audits'),
    [ValidateRange(60, 7200)]
    [int]$TimeoutSeconds = 1200,
    [string]$AgyPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-FullPath([string]$PathValue) {
    return [System.IO.Path]::GetFullPath($PathValue).TrimEnd('\', '/')
}

function Invoke-ReadOnlyGit([string]$WorkingTree, [string[]]$Arguments) {
    $value = & git -C $WorkingTree @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git inspection failed: git $($Arguments -join ' ')" }
    return ($value -join "`n").Trim()
}

function Get-GitState([string]$WorkingTree) {
    $head = Invoke-ReadOnlyGit $WorkingTree @('rev-parse', 'HEAD')
    $dirty = Invoke-ReadOnlyGit $WorkingTree @('status', '--porcelain=v1')
    & git -C $WorkingTree diff --cached --quiet
    $stagingClean = $LASTEXITCODE -eq 0
    return [ordered]@{ head = $head; dirty = $dirty; staging_clean = $stagingClean }
}

function Get-AntigravityProjectId([string]$WorkingTree) {
    $cachePath = Join-Path $env:USERPROFILE '.gemini\projects.json'
    if (-not (Test-Path -LiteralPath $cachePath -PathType Leaf)) {
        throw "Antigravity project cache is unavailable: $cachePath"
    }
    try { $cache = Get-Content -LiteralPath $cachePath -Raw | ConvertFrom-Json -AsHashtable }
    catch { throw 'Antigravity project cache is malformed; refusing to guess a Project ID.' }
    if ($null -eq $cache.projects -or -not ($cache.projects -is [hashtable])) {
        throw 'Antigravity project cache has no projects mapping; refusing to guess a Project ID.'
    }
    $key = (Resolve-FullPath $WorkingTree).Replace('/', '\').ToLowerInvariant()
    $projectId = $cache.projects[$key]
    if (-not ($projectId -is [string]) -or [string]::IsNullOrWhiteSpace($projectId)) {
        throw 'No Antigravity Project ID is mapped to this audit worktree.'
    }
    if ($projectId -notmatch '^[A-Za-z0-9._-]{1,200}$') {
        throw 'Antigravity Project ID has an unsafe format.'
    }
    return $projectId
}

function Assert-OutsideWorktrees([string]$Candidate, [string[]]$Worktrees) {
    $resolved = Resolve-FullPath $Candidate
    foreach ($worktree in $Worktrees) {
        $root = Resolve-FullPath $worktree
        if ($resolved.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
            $resolved.StartsWith($root + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw 'OutputRoot must be outside both PokeAdvice worktrees.'
        }
    }
    return $resolved
}

$audit = Resolve-FullPath $AuditWorktree
$production = Resolve-FullPath $ProductionWorktree
if (-not (Test-Path -LiteralPath $audit -PathType Container)) { throw 'Audit worktree does not exist.' }
if (-not (Test-Path -LiteralPath $production -PathType Container)) { throw 'Production worktree does not exist.' }
if ($audit.Equals($production, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Audit worktree must not be the production worktree.' }
if (-not (Test-Path -LiteralPath $PromptPath -PathType Leaf)) { throw 'Audit prompt file does not exist.' }

$auditTopLevel = Invoke-ReadOnlyGit $audit @('rev-parse', '--show-toplevel')
if (-not (Resolve-FullPath $auditTopLevel).Equals($audit, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Configured audit path is not its Git worktree root.' }
$productionTopLevel = Invoke-ReadOnlyGit $production @('rev-parse', '--show-toplevel')
if (-not (Resolve-FullPath $productionTopLevel).Equals($production, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Configured production path is not its Git worktree root.' }

$before = Get-GitState $audit
if ($before.head -ne $ExpectedHead) { throw "BASELINE_MISMATCH: expected $ExpectedHead, observed $($before.head)" }
if ($before.dirty) { throw 'DIRTY_WORKTREE: audit worktree has tracked or untracked changes.' }
if (-not $before.staging_clean) { throw 'STAGED_CHANGES_PRESENT: audit worktree index is not clean.' }

if ([string]::IsNullOrWhiteSpace($AgyPath)) {
    $command = Get-Command agy -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw 'Antigravity CLI executable "agy" is not available on PATH.' }
    $AgyPath = $command.Source
}
if (-not (Test-Path -LiteralPath $AgyPath -PathType Leaf)) { throw 'Antigravity CLI executable is unavailable.' }
$projectId = Get-AntigravityProjectId $audit
$output = Assert-OutsideWorktrees $OutputRoot @($audit, $production)

$runId = '{0:yyyyMMddTHHmmssZ}-{1}' -f [DateTime]::UtcNow, ([guid]::NewGuid().ToString('N').Substring(0, 8))
$runDirectory = Join-Path $output (Join-Path 'runs' $runId)
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$resultPath = Join-Path $runDirectory 'result.json'
$stderrPath = Join-Path $runDirectory 'stderr.log'
$metadataPath = Join-Path $runDirectory 'run-metadata.json'
$promptSnapshotPath = Join-Path $runDirectory 'prompt.txt'
Copy-Item -LiteralPath $PromptPath -Destination $promptSnapshotPath
$prompt = Get-Content -LiteralPath $PromptPath -Raw

$start = [DateTime]::UtcNow
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $AgyPath
$psi.WorkingDirectory = $audit
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
[void]$psi.ArgumentList.Add("--project=$projectId")
[void]$psi.ArgumentList.Add('--add-dir')
[void]$psi.ArgumentList.Add($audit)
[void]$psi.ArgumentList.Add('--mode')
[void]$psi.ArgumentList.Add('plan')
[void]$psi.ArgumentList.Add('--sandbox')
[void]$psi.ArgumentList.Add('--print')
[void]$psi.ArgumentList.Add($prompt)
[void]$psi.ArgumentList.Add('--output-format')
[void]$psi.ArgumentList.Add('json')
[void]$psi.ArgumentList.Add('--print-timeout')
[void]$psi.ArgumentList.Add("${TimeoutSeconds}s")

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $psi
if (-not $process.Start()) { throw 'Antigravity process did not start.' }
$stdoutTask = $process.StandardOutput.ReadToEndAsync()
$stderrTask = $process.StandardError.ReadToEndAsync()
if (-not $process.WaitForExit(($TimeoutSeconds + 60) * 1000)) {
    $process.Kill($true)
    $process.WaitForExit()
    $timedOut = $true
} else { $timedOut = $false }
$stdout = $stdoutTask.GetAwaiter().GetResult()
$stderr = $stderrTask.GetAwaiter().GetResult()
[System.IO.File]::WriteAllText($resultPath, $stdout, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText($stderrPath, $stderr, [System.Text.UTF8Encoding]::new($false))
$end = [DateTime]::UtcNow

$parsed = $null
$parseError = $null
try { $parsed = $stdout | ConvertFrom-Json -AsHashtable } catch { $parseError = $_.Exception.Message }
$response = if ($null -ne $parsed -and $parsed.ContainsKey('response')) { [string]$parsed.response } else { '' }
$terminalStatus = if ($null -ne $parsed -and $parsed.ContainsKey('status')) { [string]$parsed.status } else { $null }
$conversationId = if ($null -ne $parsed -and $parsed.ContainsKey('conversation_id')) { [string]$parsed.conversation_id } else { $null }
$usage = if ($null -ne $parsed -and $parsed.ContainsKey('usage')) { $parsed.usage } else { $null }
$stderrSafetyEvents = @($stderr -split "`r?`n" | Where-Object { $_ -match '(?i)(denied|permission|not permitted|blocked)' })
$reportedDeniedActions = @()
if ($null -ne $parsed -and $parsed.ContainsKey('denied_actions') -and $parsed.denied_actions -is [System.Collections.IEnumerable]) {
    $reportedDeniedActions = @($parsed.denied_actions | ForEach-Object {
        if ($_ -is [hashtable]) { [ordered]@{ action = $_.action; display_name = $_.display_name } }
        else { [string]$_ }
    })
}
$safetyEvents = @($stderrSafetyEvents) + @($reportedDeniedActions | ConvertTo-Json -Compress)
$criticalBlockage = @($safetyEvents | Where-Object { $_ -match '(?i)(read_file|view_file|code_search|grep|run_command|command)' })
$after = Get-GitState $audit
$integrityOk = $after.head -eq $before.head -and $after.head -eq $ExpectedHead -and -not $after.dirty -and $after.staging_clean

if (-not $integrityOk -or $timedOut -or $process.ExitCode -ne 0 -or $null -eq $parsed -or $terminalStatus -ne 'SUCCESS' -or [string]::IsNullOrWhiteSpace($response)) {
    $classification = 'FAIL'
} elseif ($criticalBlockage.Count -gt 0 -or $response -match '(?im)^STATUS:\s*(PARTIAL|BLOCKED)\b') {
    $classification = 'PARTIAL'
} else {
    $classification = 'PASS'
}

$metadata = [ordered]@{
    run_id = $runId; started_at = $start.ToString('o'); finished_at = $end.ToString('o')
    duration_seconds = [math]::Round(($end - $start).TotalSeconds, 3); classification = $classification
    audit_worktree = $audit; expected_head = $ExpectedHead; head_before = $before.head; head_after = $after.head
    dirty_before = [bool]$before.dirty; dirty_after = [bool]$after.dirty
    staging_clean_before = $before.staging_clean; staging_clean_after = $after.staging_clean
    antigravity_project_id = $projectId; conversation_id = $conversationId; antigravity_terminal_status = $terminalStatus
    exit_code = $process.ExitCode; timed_out = $timedOut; token_usage = $usage; denied_actions = $reportedDeniedActions; denied_action_diagnostics = $stderrSafetyEvents
    result_path = $resultPath; stderr_path = $stderrPath; prompt_snapshot_path = $promptSnapshotPath; parse_error = $parseError
}
$metadata | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $metadataPath -Encoding utf8
Write-Output "classification=$classification"
Write-Output "run_directory=$runDirectory"
if ($classification -eq 'FAIL') { exit 1 }
