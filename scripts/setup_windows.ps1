$ErrorActionPreference = "Stop"

Write-Host "== AICharacter bootstrap ==" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Không tìm thấy Git trong PATH."
}

try {
    py -3.10 --version | Out-Host
} catch {
    throw "Cần Python 3.10. Cài Python 3.10 rồi chạy lại script."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Tạo .venv cho AICharacter..."
    py -3.10 -m venv .venv
}

$AppPython = Resolve-Path ".venv\Scripts\python.exe"
& $AppPython -m pip install --upgrade pip
& $AppPython -m pip install -r requirements.txt

if (-not (Test-Path "external\MuseTalk\.git")) {
    New-Item -ItemType Directory -Force -Path "external" | Out-Null
    Write-Host "Clone MuseTalk upstream..."
    git clone https://github.com/TMElyralab/MuseTalk.git external/MuseTalk
} else {
    Write-Host "MuseTalk đã tồn tại, bỏ qua clone."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Đã tạo .env từ .env.example"
}

New-Item -ItemType Directory -Force -Path "data\characters" | Out-Null
New-Item -ItemType Directory -Force -Path "data\jobs" | Out-Null
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

Write-Host ""
Write-Host "Bootstrap xong." -ForegroundColor Green
Write-Host "Tiếp theo chạy: .\scripts\setup_musetalk_windows.ps1"
