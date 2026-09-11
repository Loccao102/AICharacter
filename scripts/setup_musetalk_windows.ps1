$ErrorActionPreference = "Stop"

$MuseDir = "external\MuseTalk"
$MusePython = "$MuseDir\.venv\Scripts\python.exe"

if (-not (Test-Path "$MuseDir\requirements.txt")) {
    throw "Không thấy MuseTalk. Hãy chạy .\scripts\setup_windows.ps1 trước."
}

if (-not (Test-Path $MusePython)) {
    Write-Host "Tạo Python 3.10 venv cho MuseTalk..." -ForegroundColor Cyan
    py -3.10 -m venv "$MuseDir\.venv"
}

& $MusePython -m pip install --upgrade pip wheel setuptools

Write-Host "Cài PyTorch CUDA 11.8 theo khuyến nghị MuseTalk upstream..." -ForegroundColor Cyan
& $MusePython -m pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

Write-Host "Cài MuseTalk requirements..." -ForegroundColor Cyan
& $MusePython -m pip install -r "$MuseDir\requirements.txt"

Write-Host "Cài MMLab packages..." -ForegroundColor Cyan
& $MusePython -m pip install --no-cache-dir -U openmim
& $MusePython -m mim install mmengine
& $MusePython -m mim install "mmcv==2.0.1"
& $MusePython -m mim install "mmdet==3.1.0"
& $MusePython -m mim install "mmpose==1.1.0"

Write-Host ""
Write-Host "MuseTalk Python environment đã cài xong." -ForegroundColor Green
Write-Host "Bước tiếp theo:"
Write-Host "  cd external\MuseTalk"
Write-Host "  .\download_weights.bat"
Write-Host "  cd ..\.."
Write-Host "  .\.venv\Scripts\python.exe scripts\verify_system.py"
