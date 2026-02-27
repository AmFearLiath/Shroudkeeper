<#
.SYNOPSIS
    Erstellt ein Release-Paket für GitHub Releases.

.DESCRIPTION
    Dieses Skript:
    1. Führt PyInstaller Build aus (optional)
    2. Erstellt ein ZIP-Archiv der kompilierten Anwendung
    3. Generiert SHA256-Prüfsummen
    4. Bereitet die Dateien für GitHub Release vor

.PARAMETER Version
    Die Versionsnummer für das Release (z.B. "1.0.0")

.PARAMETER SkipBuild
    Überspringt den PyInstaller-Build und verwendet vorhandene Dateien

.EXAMPLE
    .\create-release.ps1 -Version "1.0.0"
    .\create-release.ps1 -Version "1.0.0" -SkipBuild
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# Pfade
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistPath = Join-Path $ProjectRoot "shroudkeeper\dist\Shroudkeeper"
$SpecFile = Join-Path $ProjectRoot "shroudkeeper\Shroudkeeper.spec"
$ReleasesDir = Join-Path $ProjectRoot "releases"
$ZipName = "Shroudkeeper-v$Version-win64.zip"
$ZipPath = Join-Path $ReleasesDir $ZipName
$ChecksumFile = Join-Path $ReleasesDir "Shroudkeeper-v$Version-win64.sha256"
$ReleaseNotesFile = Join-Path $ReleasesDir "release-notes-v$Version.md"

Write-Host "=== Shroudkeeper Release Builder ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Yellow
Write-Host ""

# Releases-Verzeichnis erstellen
if (-not (Test-Path $ReleasesDir)) {
    New-Item -ItemType Directory -Path $ReleasesDir -Force | Out-Null
    Write-Host "[OK] Releases-Verzeichnis erstellt" -ForegroundColor Green
}

# Build (optional)
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host ">> PyInstaller Build starten..." -ForegroundColor Cyan
    
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-Error "Python venv nicht gefunden: $VenvPython"
        exit 1
    }
    
    Push-Location (Join-Path $ProjectRoot "shroudkeeper")
    try {
        & $VenvPython -m PyInstaller $SpecFile --noconfirm
        if ($LASTEXITCODE -ne 0) {
            Write-Error "PyInstaller Build fehlgeschlagen!"
            exit 1
        }
        Write-Host "[OK] Build erfolgreich" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "[SKIP] Build übersprungen" -ForegroundColor Yellow
}

# Prüfen ob dist-Verzeichnis existiert
if (-not (Test-Path $DistPath)) {
    Write-Error "Dist-Verzeichnis nicht gefunden: $DistPath"
    exit 1
}

# ZIP erstellen
Write-Host ""
Write-Host ">> ZIP-Archiv erstellen..." -ForegroundColor Cyan

# Vorhandenes ZIP löschen
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}

# ZIP mit Compress-Archive erstellen
Compress-Archive -Path "$DistPath\*" -DestinationPath $ZipPath -CompressionLevel Optimal
Write-Host "[OK] ZIP erstellt: $ZipName" -ForegroundColor Green

# ZIP-Größe anzeigen
$ZipSize = (Get-Item $ZipPath).Length
$ZipSizeMB = [math]::Round($ZipSize / 1MB, 2)
Write-Host "     Größe: $ZipSizeMB MB" -ForegroundColor Gray

# SHA256-Prüfsumme erstellen
Write-Host ""
Write-Host ">> SHA256-Prüfsumme erstellen..." -ForegroundColor Cyan

$Hash = (Get-FileHash -Path $ZipPath -Algorithm SHA256).Hash.ToLower()
"$Hash  $ZipName" | Out-File -FilePath $ChecksumFile -Encoding utf8 -NoNewline
Write-Host "[OK] SHA256: $Hash" -ForegroundColor Green

# Zusammenfassung
Write-Host ""
Write-Host "=== Release bereit ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dateien für GitHub Release:" -ForegroundColor Yellow
Write-Host "  - $ZipPath" -ForegroundColor White
Write-Host "  - $ChecksumFile" -ForegroundColor White
Write-Host ""
Write-Host "GitHub Release erstellen:" -ForegroundColor Yellow
Write-Host "  1. Gehe zu: https://github.com/[username]/shroudkeeper/releases/new" -ForegroundColor Gray
Write-Host "  2. Tag: v$Version" -ForegroundColor Gray
Write-Host "  3. Titel: Shroudkeeper v$Version" -ForegroundColor Gray
Write-Host "  4. Dateien hochladen (Drag & Drop)" -ForegroundColor Gray
Write-Host ""

# Release Notes Template ausgeben
$ReleaseNotesTemplate = @"
## Shroudkeeper v$Version

### Download
- **Windows 64-bit**: $ZipName
- **SHA256**: $Hash

### Installation
1. ZIP-Datei entpacken
2. Shroudkeeper.exe starten

### Änderungen
- 

### Bekannte Probleme
- 
"@

$ReleaseNotesTemplate | Out-File -FilePath $ReleaseNotesFile -Encoding utf8
Write-Host "[OK] Release Notes gespeichert: $ReleaseNotesFile" -ForegroundColor Green

Write-Host "Release Notes Template:" -ForegroundColor Yellow
Write-Host $ReleaseNotesTemplate -ForegroundColor Gray
Write-Host ""
