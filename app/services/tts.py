from __future__ import annotations

import asyncio
import re
import subprocess
import wave
from pathlib import Path

import edge_tts

from app.settings import Settings


class EdgeTTSService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def synthesize(
        self,
        text: str,
        audio_path: Path,
        subtitle_path: Path,
        voice: str | None = None,
    ) -> None:
        voice = voice or self.settings.edge_tts_voice
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=self.settings.edge_tts_rate,
            volume=self.settings.edge_tts_volume,
        )
        submaker = edge_tts.SubMaker()

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        with audio_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    submaker.feed(chunk)

        subtitle_path.write_text(submaker.get_srt(), encoding="utf-8")


class VieNeuTTSService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _wav_duration(path: Path) -> float:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            return handle.getnframes() / float(rate) if rate else 0.0

    @staticmethod
    def _srt_time(seconds: float) -> str:
        millis = max(0, int(round(seconds * 1000)))
        hours, millis = divmod(millis, 3_600_000)
        minutes, millis = divmod(millis, 60_000)
        secs, millis = divmod(millis, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @classmethod
    def _write_proportional_srt(cls, text: str, audio_path: Path, subtitle_path: Path) -> None:
        duration = max(cls._wav_duration(audio_path), 0.1)
        chunks = [
            item.strip()
            for item in re.split(r"(?<=[.!?…])\s+|(?<=,)\s+", text.strip())
            if item.strip()
        ]
        if not chunks:
            chunks = [text.strip()]

        weights = [max(len(item), 1) for item in chunks]
        total_weight = max(sum(weights), 1)
        cursor = 0.0
        lines: list[str] = []
        for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
            if index == len(chunks):
                end = duration
            else:
                end = min(duration, cursor + duration * weight / total_weight)
            lines.extend(
                [
                    str(index),
                    f"{cls._srt_time(cursor)} --> {cls._srt_time(end)}",
                    chunk,
                    "",
                ]
            )
            cursor = end
        subtitle_path.write_text("\n".join(lines), encoding="utf-8")

    def synthesize(
        self,
        text: str,
        audio_path: Path,
        subtitle_path: Path,
        *,
        reference_audio: Path | None = None,
        reference_text: str = "",
        preset_voice: str = "",
    ) -> None:
        python = self.settings.vieneu_python.resolve()
        worker = self.settings.vieneu_worker.resolve()
        if not python.exists():
            raise RuntimeError(
                "VieNeu local TTS chưa được setup. Chạy .\\scripts\\setup_vieneu_windows.ps1 trước."
            )
        if not worker.exists():
            raise RuntimeError(f"Không tìm thấy VieNeu worker: {worker}")

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        text_file = audio_path.parent / "tts_text.txt"
        text_file.write_text(text, encoding="utf-8")

        command = [
            str(python),
            str(worker),
            "--text-file",
            str(text_file),
            "--output",
            str(audio_path.resolve()),
            "--backend",
            self.settings.vieneu_backend,
        ]

        if reference_audio is not None:
            ref_text_file = audio_path.parent / "tts_reference_text.txt"
            ref_text_file.write_text(reference_text.strip(), encoding="utf-8")
            command.extend(
                [
                    "--ref-audio",
                    str(reference_audio.resolve()),
                    "--ref-text-file",
                    str(ref_text_file.resolve()),
                ]
            )
        elif preset_voice:
            command.extend(["--preset", preset_voice])

        completed = subprocess.run(
            command,
            cwd=self.settings.vieneu_worker.parent.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.settings.vieneu_timeout_sec,
        )
        if completed.returncode != 0 or not audio_path.exists():
            details = (completed.stderr or completed.stdout or "unknown VieNeu error")[-3000:]
            raise RuntimeError(f"VieNeu TTS thất bại.\n{details}")

        self._write_proportional_srt(text, audio_path, subtitle_path)


class HybridTTSService:
    """Local VieNeu is the default; Edge is only an explicit compatibility path."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.local = VieNeuTTSService(settings)
        self.edge = EdgeTTSService(settings)

    @staticmethod
    def _is_edge_voice(voice: str) -> bool:
        lowered = voice.lower()
        return lowered.startswith("edge:") or ("-neural" in lowered and not lowered.startswith("vieneu:"))

    def synthesize(
        self,
        text: str,
        audio_wav: Path,
        subtitle_path: Path,
        *,
        voice: str | None = None,
        reference_audio: Path | None = None,
        reference_text: str = "",
    ) -> str:
        selected = (voice or "").strip()

        # An explicit edge: prefix always wins. Existing vi-VN-*-Neural values are
        # retained for backward compatibility, but new characters default to VieNeu.
        if selected and self._is_edge_voice(selected) and reference_audio is None:
            edge_voice = selected.removeprefix("edge:")
            mp3_path = audio_wav.with_suffix(".edge.mp3")
            asyncio.run(
                self.edge.synthesize(
                    text=text,
                    audio_path=mp3_path,
                    subtitle_path=subtitle_path,
                    voice=edge_voice,
                )
            )
            command = [
                self.settings.ffmpeg_bin,
                "-y",
                "-i",
                str(mp3_path.resolve()),
                "-ac",
                "1",
                "-ar",
                "16000",
                str(audio_wav.resolve()),
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.returncode != 0 or not audio_wav.exists():
                raise RuntimeError("Không convert được Edge TTS sang WAV.\n" + completed.stderr[-1800:])
            return "edge"

        preset = self.settings.vieneu_preset_voice
        if selected.startswith("vieneu:") and selected not in {"vieneu:clone", "vieneu:"}:
            preset = selected.split(":", 1)[1].strip()

        self.local.synthesize(
            text=text,
            audio_path=audio_wav,
            subtitle_path=subtitle_path,
            reference_audio=reference_audio,
            reference_text=reference_text,
            preset_voice=preset,
        )
        return "vieneu-clone" if reference_audio is not None else "vieneu"
