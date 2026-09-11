$ErrorActionPreference = "Stop"

$MusePython = "external\MuseTalk\.venv\Scripts\python.exe"
$Downloader = "scripts\download_musetalk_weights.py"

if (-not (Test-Path $MusePython)) {
    throw "MuseTalk Python environment was not found. Run .\scripts\setup_musetalk_windows.ps1 first."
}

if (-not (Test-Path $Downloader)) {
    throw "Weight downloader script was not found. Run git pull origin main."
}

Write-Host "Installing Hugging Face download support..." -ForegroundColor Cyan
& $MusePython -m pip install "huggingface_hub[hf_xet]==0.30.2"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Hugging Face download support."
}

Write-Host "Downloading MuseTalk 1.5 weights..." -ForegroundColor Cyan
& $MusePython $Downloader
if ($LASTEXITCODE -ne 0) {
    throw "MuseTalk weight download failed. Re-run this script to resume."
}

Write-Host ""
Write-Host "Weights are ready." -ForegroundColor Green
Write-Host "Next: .\.venv\Scripts\python.exe scripts\verify_system.py"
