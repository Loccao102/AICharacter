$ErrorActionPreference = "Stop"

Write-Host "== AICharacter bootstrap ==" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found in PATH. Install Git and reopen PowerShell."
}

$AppPython = ".venv\Scripts\python.exe"

if (Test-Path $AppPython) {
    Write-Host "Using existing AICharacter virtual environment..." -ForegroundColor Cyan
    & $AppPython -c "import sys; assert sys.version_info[:2] == (3, 10), 'AICharacter requires Python 3.10, got ' + sys.version"
    if ($LASTEXITCODE -ne 0) {
        throw "Existing .venv is not Python 3.10. Delete .venv and recreate it with Python 3.10."
    }
} else {
    Write-Host "No .venv found. Looking for Python 3.10..." -ForegroundColor Cyan

    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $PyLauncher) {
        throw "Python launcher 'py' was not found. Install Python 3.10, then run: py -3.10 -m venv .venv"
    }

    & py -3.10 --version
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.10 was not found. Install it, then run: py -3.10 -m venv .venv"
    }

    Write-Host "Creating AICharacter .venv with Python 3.10..." -ForegroundColor Cyan
    & py -3.10 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv with Python 3.10."
    }
}

$AppPython = (Resolve-Path $AppPython).Path
Write-Host "App Python: $AppPython"
& $AppPython --version

Write-Host "Installing AICharacter dependencies..." -ForegroundColor Cyan
& $AppPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $AppPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements.txt." }

$MuseDir = "external\MuseTalk"
$MuseUrl = "https://github.com/TMElyralab/MuseTalk.git"
$MuseZipUrl = "https://github.com/TMElyralab/MuseTalk/archive/refs/heads/main.zip"

function Test-MuseTalkReady {
    return (Test-Path "$MuseDir\requirements.txt") -and (Test-Path "$MuseDir\scripts\inference.py")
}

function Remove-PartialMuseTalk {
    if (Test-Path $MuseDir) {
        Write-Host "Removing incomplete MuseTalk directory..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $MuseDir
    }
}

function Install-MuseTalkFromZip {
    Write-Host "Git clone failed repeatedly. Falling back to GitHub ZIP download..." -ForegroundColor Yellow

    $ZipPath = Join-Path $env:TEMP "MuseTalk-main.zip"
    $ExtractRoot = Join-Path $env:TEMP "AICharacter-MuseTalk-extract"

    if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
    if (Test-Path $ExtractRoot) { Remove-Item -Recurse -Force $ExtractRoot }

    New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
    Invoke-WebRequest -Uri $MuseZipUrl -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractRoot -Force

    $Extracted = Join-Path $ExtractRoot "MuseTalk-main"
    if (-not (Test-Path $Extracted)) {
        throw "MuseTalk ZIP was downloaded but the extracted folder was not found."
    }

    New-Item -ItemType Directory -Force -Path "external" | Out-Null
    Move-Item -Path $Extracted -Destination $MuseDir

    Remove-Item -Force $ZipPath -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $ExtractRoot -ErrorAction SilentlyContinue
}

if (-not (Test-MuseTalkReady)) {
    New-Item -ItemType Directory -Force -Path "external" | Out-Null
    Remove-PartialMuseTalk

    $CloneSucceeded = $false
    for ($Attempt = 1; $Attempt -le 3; $Attempt++) {
        Write-Host "Cloning MuseTalk upstream (attempt $Attempt/3, shallow clone)..." -ForegroundColor Cyan

        git -c http.version=HTTP/1.1 clone --depth 1 --single-branch --branch main --filter=blob:none $MuseUrl $MuseDir

        if (($LASTEXITCODE -eq 0) -and (Test-MuseTalkReady)) {
            $CloneSucceeded = $true
            break
        }

        Write-Host "Clone attempt $Attempt failed." -ForegroundColor Yellow
        Remove-PartialMuseTalk
        Start-Sleep -Seconds 2
    }

    if (-not $CloneSucceeded) {
        Install-MuseTalkFromZip
    }

    if (-not (Test-MuseTalkReady)) {
        throw "MuseTalk source is still incomplete after clone/ZIP fallback."
    }
} else {
    Write-Host "MuseTalk source already exists; skipping download."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

New-Item -ItemType Directory -Force -Path "data\characters" | Out-Null
New-Item -ItemType Directory -Force -Path "data\jobs" | Out-Null
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

Write-Host ""
Write-Host "Bootstrap completed." -ForegroundColor Green
Write-Host "Next: .\scripts\setup_musetalk_windows.ps1"
