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

if (-not (Test-Path "external\MuseTalk\.git")) {
    New-Item -ItemType Directory -Force -Path "external" | Out-Null
    Write-Host "Cloning MuseTalk upstream..." -ForegroundColor Cyan
    git clone https://github.com/TMElyralab/MuseTalk.git external/MuseTalk
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone MuseTalk." }
} else {
    Write-Host "MuseTalk already exists; skipping clone."
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
