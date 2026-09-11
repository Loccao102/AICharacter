$ErrorActionPreference = "Stop"

$AppPython = ".venv\Scripts\python.exe"
$VoiceDir = "external\vieneu"
$VoicePython = "$VoiceDir\.venv\Scripts\python.exe"

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

if (-not (Test-Path $AppPython)) {
    throw "AICharacter .venv was not found. Run .\scripts\setup_windows.ps1 first."
}

& $AppPython -c "import sys; assert sys.version_info[:2] == (3, 10), 'AICharacter requires Python 3.10'"
if ($LASTEXITCODE -ne 0) {
    throw "AICharacter .venv must use Python 3.10."
}

if (-not (Test-Path $VoicePython)) {
    Write-Host "Creating isolated VieNeu Python environment..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $VoiceDir | Out-Null
    & $AppPython -m venv "$VoiceDir\.venv"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create VieNeu virtual environment."
    }
}

Invoke-Step "Upgrading VieNeu packaging tools" {
    & $VoicePython -m pip install --upgrade pip wheel setuptools
}

Invoke-Step "Installing VieNeu-TTS v3 Turbo CPU/ONNX" {
    & $VoicePython -m pip install -r requirements-voice.txt
}

Invoke-Step "Checking VieNeu package" {
    & $VoicePython -c "import importlib.metadata; print('vieneu', importlib.metadata.version('vieneu'))"
}

Write-Host ""
Write-Host "Initializing VieNeu ONNX engine and downloading model files if needed..." -ForegroundColor Cyan
Write-Host "This first run can download a large model and may take a while." -ForegroundColor Yellow
& $VoicePython -c "from vieneu import Vieneu; v=Vieneu(backend='onnx'); print('VieNeu ONNX ready'); print('preset voices:', len(v.list_preset_voices())); v.close()"
if ($LASTEXITCODE -ne 0) {
    throw "VieNeu installed, but model initialization failed. Re-run this script to resume downloads."
}

Write-Host ""
Write-Host "VieNeu local voice engine is ready." -ForegroundColor Green
Write-Host "Restart AICharacter with: .\scripts\run.ps1"
