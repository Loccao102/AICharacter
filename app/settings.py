from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "127.0.0.1"
    app_port: int = 8000

    musetalk_dir: Path = ROOT / "external" / "MuseTalk"
    musetalk_python: Path = ROOT / "external" / "MuseTalk" / ".venv" / "Scripts" / "python.exe"
    musetalk_result_dir: Path = Path("results/aicharacter")

    ffmpeg_bin: str = "ffmpeg"
    ffmpeg_dir: str = ""

    edge_tts_voice: str = "vi-VN-NamMinhNeural"
    edge_tts_rate: str = "+5%"
    edge_tts_volume: str = "+0%"

    gpu_batch_size: int = 2
    use_fp16: bool = True
    max_gpu_workers: int = 1

    output_width: int = 1080
    output_height: int = 1920
    talking_height: int = 1200

    @property
    def characters_dir(self) -> Path:
        return ROOT / "data" / "characters"

    @property
    def jobs_dir(self) -> Path:
        return ROOT / "data" / "jobs"

    @property
    def outputs_dir(self) -> Path:
        return ROOT / "outputs"

    @property
    def web_dir(self) -> Path:
        return ROOT / "app" / "web"

    def ensure_runtime_dirs(self) -> None:
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
