$ErrorActionPreference = "Stop"

$MuseDir = "external\MuseTalk"
$MusePython = "$MuseDir\.venv\Scripts\python.exe"
$AppPython = ".venv\Scripts\python.exe"

if (-not (Test-Path "$MuseDir\requirements.txt")) {
    throw "MuseTalk was not found. Run .\scripts\setup_windows.ps1 first."
}

if (-not (Test-Path $AppPython)) {
    throw "AICharacter .venv was not found. Run .\scripts\setup_windows.ps1 first."
}

& $AppPython -c "import sys; assert sys.version_info[:2] == (3, 10), 'AICharacter requires Python 3.10, got ' + sys.version"
if ($LASTEXITCODE -ne 0) {
    throw "AICharacter .venv is not Python 3.10."
}

if (-not (Test-Path $MusePython)) {
    Write-Host "Creating MuseTalk Python 3.10 virtual environment..." -ForegroundColor Cyan
    & $AppPython -m venv "$MuseDir\.venv"
    if ($LASTEXITCODE -ne 0) { throw "Failed to create MuseTalk virtual environment." }
}

Write-Host "MuseTalk Python:" -ForegroundColor Cyan
& $MusePython --version

Write-Host "Upgrading pip/wheel/setuptools..." -ForegroundColor Cyan
& $MusePython -m pip install --upgrade pip wheel setuptools
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade MuseTalk packaging tools." }

Write-Host "Installing PyTorch CUDA 11.8 build..." -ForegroundColor Cyan
& $MusePython -m pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
if ($LASTEXITCODE -ne 0) { throw "Failed to install PyTorch CUDA 11.8 packages." }

Write-Host "Installing MuseTalk requirements..." -ForegroundColor Cyan
& $MusePython -m pip install -r "$MuseDir\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Failed to install MuseTalk requirements." }

Write-Host "Installing MMLab packages..." -ForegroundColor Cyan
& $MusePython -m pip install --no-cache-dir -U openmim
if ($LASTEXITCODE -ne 0) { throw "Failed to install openmim." }
& $MusePython -m mim install mmengine
if ($LASTEXITCODE -ne 0) { throw "Failed to install mmengine." }
& $MusePython -m mim install "mmcv==2.0.1"
if ($LASTEXITCODE -ne 0) { throw "Failed to install mmcv." }
& $MusePython -m mim install "mmdet==3.1.0"
if ($LASTEXITCODE -ne 0) { throw "Failed to install mmdet." }
& $MusePython -m mim install "mmpose==1.1.0"
if ($LASTEXITCODE -ne 0) { throw "Failed to install mmpose." }

Write-Host ""
Write-Host "MuseTalk environment setup completed." -ForegroundColor Green
Write-Host "Next commands:"
Write-Host "  cd external\MuseTalk"
Write-Host "  .\download_weights.bat"
Write-Host "  cd ..\.."
Write-Host "  .\.venv\Scripts\python.exe scripts\verify_system.py"
