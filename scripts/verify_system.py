from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSE = ROOT / "external" / "MuseTalk"
MODELS = MUSE / "models"
MUSE_PYTHON = MUSE / ".venv" / "Scripts" / "python.exe"

REQUIRED_WEIGHTS = {
    "musetalk_v15_unet": MODELS / "musetalkV15" / "unet.pth",
    "musetalk_v15_config": MODELS / "musetalkV15" / "musetalk.json",
    "sd_vae_config": MODELS / "sd-vae" / "config.json",
    "sd_vae_model": MODELS / "sd-vae" / "diffusion_pytorch_model.bin",
    "whisper_config": MODELS / "whisper" / "config.json",
    "whisper_model": MODELS / "whisper" / "pytorch_model.bin",
    "whisper_preprocessor": MODELS / "whisper" / "preprocessor_config.json",
    "dwpose": MODELS / "dwpose" / "dw-ll_ucoco_384.pth",
    "syncnet": MODELS / "syncnet" / "latentsync_syncnet.pt",
    "face_parser": MODELS / "face-parse-bisent" / "79999_iter.pth",
    "face_parser_resnet": MODELS / "face-parse-bisent" / "resnet18-5c106cde.pth",
}


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


def check_weights() -> dict:
    result: dict[str, dict] = {}
    for name, path in REQUIRED_WEIGHTS.items():
        exists = path.exists() and path.stat().st_size > 0
        result[name] = {
            "ok": exists,
            "path": str(path.relative_to(MUSE)),
            "size_mb": round(path.stat().st_size / 1024**2, 1) if exists else 0,
        }
    return result


def main() -> int:
    weights = check_weights()
    checks = {
        "python": sys.version.split()[0],
        "ffmpeg": check_command("ffmpeg"),
        "musetalk_repo": (MUSE / "scripts" / "inference.py").exists(),
        "weights_ok": all(item["ok"] for item in weights.values()),
        "weights": weights,
        "musetalk_python": check_musetalk_python(),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))

    errors = []
    if not checks["ffmpeg"]["ok"]:
        errors.append("FFmpeg chua co trong PATH")
    if not checks["musetalk_repo"]:
        errors.append("Chua co MuseTalk source")
    if not checks["weights_ok"]:
        missing = [name for name, item in weights.items() if not item["ok"]]
        errors.append("Thieu MuseTalk weights: " + ", ".join(missing))
    if not checks["musetalk_python"]["ok"]:
        errors.append("MuseTalk Python environment chua san sang")
    elif not checks["musetalk_python"].get("cuda"):
        errors.append("PyTorch trong MuseTalk khong nhin thay CUDA")

    if errors:
        print("\nCAN XU LY:")
        for item in errors:
            print(f"- {item}")
        print("\nRun: .\\scripts\\download_musetalk_weights.ps1")
        return 1

    print("\nOK: MuseTalk 1.5 environment and all required weights are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
