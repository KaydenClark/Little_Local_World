[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$TemplateMode
)

$ErrorActionPreference = 'Stop'

$requiredFiles = @(
    'AGENTS.md',
    'BLUEPRINT.md',
    'ROADMAP.md',
    'RUNBOOK.md',
    'BOOTSTRAP_CHECKLIST.md',
    'UNATTENDED_WORK_POLICY.md'
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
    'ROADMAP.md' = @(
        '## Current State',
        '## Current Goal',
        '## Verification Log'
    )
    'RUNBOOK.md' = @(
        '## Prerequisites',
        '## Run Locally',
        '## Test And Build'
    )
    'BOOTSTRAP_CHECKLIST.md' = @(
        '## Existing Project Path',
        '## New Project Path',
        '## Completion Gate'
    )
    'UNATTENDED_WORK_POLICY.md' = @(
        '## Runtime Limits',
        '## Branch Rules',
        '## Stop Conditions',
        '## Final Audit'
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

    $roadmap = Get-Content -LiteralPath (Join-Path $Root 'ROADMAP.md') -Raw
    if ($roadmap -notmatch '(?m)^\| \d{4}-\d{2}-\d{2} \|') {
        $failures.Add('ROADMAP.md Verification Log needs at least one dated project-specific row.')
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
