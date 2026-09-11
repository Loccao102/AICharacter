from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSE = ROOT / "external" / "MuseTalk"
MUSE_PYTHON = MUSE / ".venv" / "Scripts" / "python.exe"


def check_command(name: str) -> dict:
    path = shutil.which(name)
    if not path:
        return {"ok": False, "path": None}
    try:
        version = subprocess.run(
            [name, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        ).stdout.splitlines()[0]
    except Exception:
        version = "found"
    return {"ok": True, "path": path, "version": version}


def check_musetalk_python() -> dict:
    if not MUSE_PYTHON.exists():
        return {"ok": False, "error": f"missing {MUSE_PYTHON}"}
    code = (
        "import json, torch; "
        "print(json.dumps({'torch': torch.__version__, 'cuda': torch.cuda.is_available(), "
        "'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "
        "'vram_gb': round(torch.cuda.get_device_properties(0).total_memory/1024**3, 2) if torch.cuda.is_available() else 0}))"
    )
    run = subprocess.run(
        [str(MUSE_PYTHON), "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if run.returncode != 0:
        return {"ok": False, "error": run.stderr.strip()}
    return {"ok": True, **json.loads(run.stdout.strip())}


def main() -> int:
    checks = {
        "python": sys.version.split()[0],
        "ffmpeg": check_command("ffmpeg"),
        "musetalk_repo": (MUSE / "scripts" / "inference.py").exists(),
        "musetalk_unet": (MUSE / "models" / "musetalkV15" / "unet.pth").exists(),
        "musetalk_python": check_musetalk_python(),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))

    errors = []
    if not checks["ffmpeg"]["ok"]:
        errors.append("FFmpeg chưa có trong PATH")
    if not checks["musetalk_repo"]:
        errors.append("Chưa clone MuseTalk")
    if not checks["musetalk_unet"]:
        errors.append("Chưa tải MuseTalk 1.5 weights")
    if not checks["musetalk_python"]["ok"]:
        errors.append("MuseTalk Python environment chưa sẵn sàng")
    elif not checks["musetalk_python"].get("cuda"):
        errors.append("PyTorch trong MuseTalk không nhìn thấy CUDA")

    if errors:
        print("\nCẦN XỬ LÝ:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("\nOK: môi trường cơ bản đã sẵn sàng để chạy V1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
