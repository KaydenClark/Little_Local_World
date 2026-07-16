[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$TemplateMode
)

$ErrorActionPreference = 'Stop'

# LLM Workbench v2.1 control-doc set (post-adoption 2026-07-02).
$requiredFiles = @(
    'AGENTS.md',
    'BLUEPRINT.md',
    'TASKBOARD.md',
    'RUNBOOK.md'
)

$requiredHeadings = @{
    'AGENTS.md' = @(
        '## Read Scope',
        '## Edit Scope',
        '## Stop And Ask',
        '## Verification And Proof'
    )
    'BLUEPRINT.md' = @(
        '## What This Project Is',
        '## Architecture',
        '## Health Criteria'
    )
    'TASKBOARD.md' = @(
        '## Executive Brief',
        '## Ready',
        '## Proof Log'
    )
    'RUNBOOK.md' = @(
        '## Prerequisites',
        '## Run Locally',
        '## Test And Build'
    )
}

$placeholderPattern = '(?i)\[[A-Z0-9_ /.-]+\]|\b(TODO|TBD|FIXME|CHANGEME)\b|\{\{[^}]+\}\}'
$failures = [System.Collections.Generic.List[string]]::new()

foreach ($relativePath in $requiredFiles) {
    $path = Join-Path $Root $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $failures.Add("Missing required file: $relativePath")
        continue
    }

    $content = Get-Content -LiteralPath $path -Raw
    if ([string]::IsNullOrWhiteSpace($content)) {
        $failures.Add("Required file is empty: $relativePath")
        continue
    }

    if (-not $TemplateMode -and $content -match $placeholderPattern) {
        $failures.Add("Unresolved placeholder found in: $relativePath")
    }
}

foreach ($entry in $requiredHeadings.GetEnumerator()) {
    $path = Join-Path $Root $entry.Key
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }

    $content = Get-Content -LiteralPath $path -Raw
    foreach ($heading in $entry.Value) {
        if ($content -notmatch "(?m)^$([regex]::Escape($heading))\s*$") {
            $failures.Add("Missing heading '$heading' in $($entry.Key)")
        }
    }
}

if (-not $TemplateMode) {
    $agents = Get-Content -LiteralPath (Join-Path $Root 'AGENTS.md') -Raw
    if ($agents -match '\[PRIMARY_SOURCE_DIRS\]|\[TEST_DIRS\]|\[DOCS_TO_KEEP_CURRENT\]') {
        $failures.Add('AGENTS.md edit scope still contains template placeholders.')
    }

    $taskboard = Get-Content -LiteralPath (Join-Path $Root 'TASKBOARD.md') -Raw
    if ($taskboard -notmatch '(?m)^\| \d{4}-\d{2}-\d{2} \|') {
        $failures.Add('TASKBOARD.md Proof Log needs at least one dated project-specific row.')
    }
}

if ($failures.Count -gt 0) {
    Write-Host 'Workbench validation failed:' -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host " - $failure" -ForegroundColor Red
    }
    exit 1
}

if ($TemplateMode) {
    Write-Host 'Workbench template validation passed.' -ForegroundColor Green
} else {
    Write-Host 'Adopted workbench validation passed.' -ForegroundColor Green
}
Write-Host "Checked root: $Root"
Write-Host "Required files: $($requiredFiles.Count)"
