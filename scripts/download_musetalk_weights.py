from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUSE = ROOT / "external" / "MuseTalk"
MODELS = MUSE / "models"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download MuseTalk 1.5 runtime weights with the Python API.")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("HF_ENDPOINT", "https://huggingface.co"),
        help="Hugging Face endpoint. Defaults to HF_ENDPOINT or https://huggingface.co",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["HF_ENDPOINT"] = args.endpoint

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("ERROR: huggingface_hub is not installed in the MuseTalk environment.")
        return 2

    if not MUSE.exists():
        print(f"ERROR: MuseTalk repo not found: {MUSE}")
        return 2

    MODELS.mkdir(parents=True, exist_ok=True)

    downloads = [
        (
            "MuseTalk 1.5",
            "TMElyralab/MuseTalk",
            MODELS,
            ["musetalkV15/musetalk.json", "musetalkV15/unet.pth"],
        ),
        (
            "SD VAE",
            "stabilityai/sd-vae-ft-mse",
            MODELS / "sd-vae",
            ["config.json", "diffusion_pytorch_model.bin"],
        ),
        (
            "Whisper tiny",
            "openai/whisper-tiny",
            MODELS / "whisper",
            ["config.json", "pytorch_model.bin", "preprocessor_config.json"],
        ),
        (
            "DWPose",
            "yzd-v/DWPose",
            MODELS / "dwpose",
            ["dw-ll_ucoco_384.pth"],
        ),
        (
            "SyncNet",
            "ByteDance/LatentSync",
            MODELS / "syncnet",
            ["latentsync_syncnet.pt"],
        ),
        (
            "Face parser",
            "ManyOtherFunctions/face-parse-bisent",
            MODELS / "face-parse-bisent",
            ["79999_iter.pth", "resnet18-5c106cde.pth"],
        ),
    ]

    print(f"Hugging Face endpoint: {args.endpoint}")
    print(f"Target: {MODELS}")
    print("Downloads are resumable; re-run this script if the network drops.\n")

    for label, repo_id, local_dir, patterns in downloads:
        local_dir.mkdir(parents=True, exist_ok=True)
        print(f"== {label} ==")
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            allow_patterns=patterns,
            max_workers=4,
        )
        print(f"OK: {label}\n")

    required = [
        MODELS / "musetalkV15" / "unet.pth",
        MODELS / "musetalkV15" / "musetalk.json",
        MODELS / "sd-vae" / "config.json",
        MODELS / "sd-vae" / "diffusion_pytorch_model.bin",
        MODELS / "whisper" / "config.json",
        MODELS / "whisper" / "pytorch_model.bin",
        MODELS / "whisper" / "preprocessor_config.json",
        MODELS / "dwpose" / "dw-ll_ucoco_384.pth",
        MODELS / "syncnet" / "latentsync_syncnet.pt",
        MODELS / "face-parse-bisent" / "79999_iter.pth",
        MODELS / "face-parse-bisent" / "resnet18-5c106cde.pth",
    ]
    missing = [path for path in required if not path.exists() or path.stat().st_size == 0]
    if missing:
        print("ERROR: Some required weights are still missing:")
        for path in missing:
            print(f"  - {path.relative_to(MUSE)}")
        return 1

    unet_gb = (MODELS / "musetalkV15" / "unet.pth").stat().st_size / 1024**3
    print(f"MuseTalk 1.5 UNet: {unet_gb:.2f} GB")
    print("All required MuseTalk 1.5 weights are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
