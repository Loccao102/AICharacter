$ErrorActionPreference = "Stop"

$AppPython = ".venv\Scripts\python.exe"

if (-not (Test-Path $AppPython)) {
    throw "AICharacter .venv was not found. Run .\scripts\setup_windows.ps1 first."
}

& $AppPython -c "import sys; assert sys.version_info[:2] == (3, 10), 'AICharacter requires Python 3.10, got ' + sys.version"
if ($LASTEXITCODE -ne 0) {
    throw "AICharacter .venv is not Python 3.10."
}

& $AppPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
