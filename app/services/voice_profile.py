from __future__ import annotations

import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.settings import Settings


@dataclass(frozen=True)
class PreparedVoiceReference:
    source_wav: Path
    reference_wav: Path
    source_duration_sec: float
    reference_duration_sec: float


class VoiceReferencePreparer:
    """Normalize an uploaded recording and extract a short VieNeu clone reference."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _duration(path: Path) -> float:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            return frames / float(rate) if rate else 0.0

    def _run_ffmpeg(self, command: list[str], label: str) -> None:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"{label} thất bại.\n{completed.stderr[-1800:]}")

    def prepare(
        self,
        input_file: BinaryIO,
        original_name: str,
        work_dir: Path,
        *,
        max_reference_seconds: float = 8.0,
    ) -> PreparedVoiceReference:
        work_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(original_name or "voice-upload.bin").suffix.lower()
        if suffix not in {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mp4"}:
            suffix = ".bin"

        raw_path = work_dir / f"voice-upload{suffix}"
        source_wav = work_dir / "voice-source.wav"
        reference_wav = work_dir / "voice-reference.wav"

        try:
            input_file.seek(0)
        except (AttributeError, OSError):
            pass
        with raw_path.open("wb") as destination:
            shutil.copyfileobj(input_file, destination)

        if raw_path.stat().st_size <= 0:
            raise ValueError("File giọng nói rỗng")

        # Keep a normalized full recording for future multi-reference/fine-tune work.
        self._run_ffmpeg(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-i",
                str(raw_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(source_wav),
            ],
            "Chuẩn hóa voice source",
        )

        source_duration = self._duration(source_wav)
        if source_duration < 3.0:
            raise ValueError("Voice sample cần ít nhất khoảng 3 giây lời nói")
        if source_duration > 300.0:
            raise ValueError("Voice sample V1 tối đa 5 phút")

        # VieNeu v3 Turbo works best with a short 3-8s clean reference. Remove leading
        # silence and take the first voiced window while keeping the full source above.
        self._run_ffmpeg(
            [
                self.settings.ffmpeg_bin,
                "-y",
                "-i",
                str(source_wav),
                "-af",
                "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB",
                "-t",
                f"{max_reference_seconds:.1f}",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(reference_wav),
            ],
            "Tạo voice reference",
        )

        reference_duration = self._duration(reference_wav)
        if reference_duration < 2.5:
            raise ValueError(
                "Không lấy được đủ lời nói sau khi bỏ silence. Hãy thu clip rõ tiếng hơn."
            )

        return PreparedVoiceReference(
            source_wav=source_wav,
            reference_wav=reference_wav,
            source_duration_sec=source_duration,
            reference_duration_sec=reference_duration,
        )
