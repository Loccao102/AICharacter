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
