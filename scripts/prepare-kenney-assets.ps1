[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression.FileSystem

$assetRoot = Join-Path $Root 'src\agent_town\assets\kenney'
$sources = @(
    @{
        Zip = 'kenney_roguelike-characters.zip'
        Entry = 'Spritesheet/roguelikeChar_transparent.png'
        Output = 'characters.png'
    },
    @{
        Zip = 'kenney_roguelike-rpg-pack.zip'
        Entry = 'Spritesheet/roguelikeSheet_transparent.png'
        Output = 'rpg_tiles.png'
    },
    @{
        Zip = 'kenney_emotes-pack.zip'
        Entry = 'Spritesheets/pixel_style1.png'
        Output = 'emotes.png'
    },
    @{
        Zip = 'kenney_emotes-pack.zip'
        Entry = 'Spritesheets/pixel_style1.xml'
        Output = 'emotes.xml'
    }
)

function Read-ZipEntryBytes {
    param(
        [Parameter(Mandatory = $true)][string]$ZipPath,
        [Parameter(Mandatory = $true)][string]$EntryName
    )

    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $entry = $archive.GetEntry($EntryName)
        if ($null -eq $entry) {
            throw "Missing zip entry '$EntryName' in '$ZipPath'."
        }

        $stream = $entry.Open()
        try {
            $memory = [System.IO.MemoryStream]::new()
            try {
                $stream.CopyTo($memory)
                return $memory.ToArray()
            }
            finally {
                $memory.Dispose()
            }
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Test-SameBytes {
    param(
        [Parameter(Mandatory = $true)][byte[]]$Left,
        [Parameter(Mandatory = $true)][byte[]]$Right
    )

    if ($Left.Length -ne $Right.Length) {
        return $false
    }

    for ($index = 0; $index -lt $Left.Length; $index += 1) {
        if ($Left[$index] -ne $Right[$index]) {
            return $false
        }
    }

    return $true
}

New-Item -ItemType Directory -Path $assetRoot -Force | Out-Null

$prepared = 0
$verified = 0

foreach ($source in $sources) {
    $zipPath = Join-Path $Root $source.Zip
    if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) {
        throw "Missing source zip: $($source.Zip)"
    }

    $outputPath = Join-Path $assetRoot $source.Output
    $expected = Read-ZipEntryBytes -ZipPath $zipPath -EntryName $source.Entry

    if (Test-Path -LiteralPath $outputPath -PathType Leaf) {
        $current = [System.IO.File]::ReadAllBytes($outputPath)
        if (Test-SameBytes -Left $current -Right $expected) {
            $verified += 1
            Write-Host "Verified $($source.Output)"
            continue
        }

        if (-not $Force) {
            throw "Asset differs from source zip: $($source.Output). Re-run with -Force to replace it."
        }
    }

    [System.IO.File]::WriteAllBytes($outputPath, $expected)
    $prepared += 1
    Write-Host "Prepared $($source.Output)"
}

Write-Host "Kenney assets ready. Prepared: $prepared. Verified: $verified."
