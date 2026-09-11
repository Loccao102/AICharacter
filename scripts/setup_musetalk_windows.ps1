$ErrorActionPreference = "Stop"

$MuseDir = "external\MuseTalk"
$MusePython = "$MuseDir\.venv\Scripts\python.exe"
$AppPython = ".venv\Scripts\python.exe"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host $Name -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

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

Invoke-Step "Upgrading pip/wheel/setuptools" {
    & $MusePython -m pip install --upgrade pip wheel "setuptools<82"
}

Invoke-Step "Installing PyTorch CUDA 11.8 build" {
    & $MusePython -m pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
}

Invoke-Step "Installing MuseTalk requirements" {
    & $MusePython -m pip install -r "$MuseDir\requirements.txt"
}

Invoke-Step "Installing openmim" {
    & $MusePython -m pip install --no-cache-dir -U openmim
}

Invoke-Step "Installing mmengine" {
    & $MusePython -m mim install mmengine
}

Invoke-Step "Installing mmcv 2.0.1" {
    & $MusePython -m mim install "mmcv==2.0.1"
}

Invoke-Step "Installing mmdet 3.1.0" {
    & $MusePython -m mim install "mmdet==3.1.0"
}

# mmpose 1.1.0 depends on chumpy 0.70. chumpy's legacy setup.py imports pip,
# which breaks inside modern PEP 517 build isolation.
# Do NOT probe with `import chumpy` here: on Windows PowerShell 5.1 a failed
# native stderr probe can be promoted to NativeCommandError when ErrorActionPreference=Stop.
Write-Host "Checking chumpy workaround for mmpose..." -ForegroundColor Cyan
& $MusePython -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('chumpy') else 1)"
$ChumpyInstalled = ($LASTEXITCODE -eq 0)

if (-not $ChumpyInstalled) {
    Invoke-Step "Installing chumpy 0.70 without build isolation" {
        & $MusePython -m pip install --no-build-isolation "chumpy==0.70"
    }
} else {
    Write-Host "chumpy package is already present; skipping workaround."
}

Invoke-Step "Installing mmpose 1.1.0" {
    & $MusePython -m mim install "mmpose==1.1.0"
}

Write-Host ""
Write-Host "Verifying MMLab imports..." -ForegroundColor Cyan
& $MusePython -c "import torch, mmengine, mmcv, mmdet, mmpose; print('torch', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('mmcv', mmcv.__version__); print('mmdet', mmdet.__version__); print('mmpose', mmpose.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "MuseTalk dependencies installed but import verification failed."
}

Write-Host ""
Write-Host "MuseTalk environment setup completed." -ForegroundColor Green
Write-Host "Next commands:"
Write-Host "  cd external\MuseTalk"
Write-Host "  .\download_weights.bat"
Write-Host "  cd ..\.."
Write-Host "  .\.venv\Scripts\python.exe scripts\verify_system.py"
