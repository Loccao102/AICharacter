import os
import subprocess
from pathlib import Path

import yaml

from app.settings import Settings


class MuseTalkError(RuntimeError):
    pass


class MuseTalkService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _python(self) -> str:
        configured = self.settings.musetalk_python
        if configured.exists():
            return str(configured.resolve())
        raise MuseTalkError(
            "Không tìm thấy Python của MuseTalk. Hãy chạy scripts/setup_musetalk_windows.ps1 "
            "hoặc sửa MUSETALK_PYTHON trong .env"
        )

    def validate(self) -> None:
        root = self.settings.musetalk_dir.resolve()
        required = [
            root / "scripts" / "inference.py",
            root / "models" / "musetalkV15" / "unet.pth",
            root / "models" / "musetalkV15" / "musetalk.json",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise MuseTalkError(
                "MuseTalk/model chưa sẵn sàng:\n- " + "\n- ".join(missing)
            )

    def generate(self, character_image: Path, audio_path: Path, work_dir: Path) -> Path:
        self.validate()
        root = self.settings.musetalk_dir.resolve()
        work_dir = work_dir.resolve()
        result_dir = work_dir / "musetalk_results"
        result_dir.mkdir(parents=True, exist_ok=True)

        output_name = "talking.mp4"
        config_path = work_dir / "musetalk_task.yaml"
        config = {
            "task_0": {
                "video_path": str(character_image.resolve()),
                "audio_path": str(audio_path.resolve()),
                "result_name": output_name,
            }
        }
        config_path.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        command = [
            self._python(),
            "-m",
            "scripts.inference",
            "--inference_config",
            str(config_path),
            "--result_dir",
            str(result_dir),
            "--unet_model_path",
            str(root / "models" / "musetalkV15" / "unet.pth"),
            "--unet_config",
            str(root / "models" / "musetalkV15" / "musetalk.json"),
            "--version",
            "v15",
            "--batch_size",
            str(max(1, self.settings.gpu_batch_size)),
        ]
        if self.settings.use_fp16:
            command.append("--use_float16")
        if self.settings.ffmpeg_dir.strip():
            command.extend(["--ffmpeg_path", self.settings.ffmpeg_dir])

        env = os.environ.copy()
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        log_path = work_dir / "musetalk.log"
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise MuseTalkError(
                f"MuseTalk thất bại (exit {completed.returncode}). Xem log: {log_path}"
            )

        output = result_dir / "v15" / output_name
        if not output.exists():
            raise MuseTalkError(
                f"MuseTalk chạy xong nhưng không thấy output: {output}. Xem {log_path}"
            )
        return output
