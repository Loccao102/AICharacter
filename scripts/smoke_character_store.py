from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import struct
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from app.storage import CharacterStore


def make_image(color: tuple[int, int, int]) -> BytesIO:
    buffer = BytesIO()
    Image.new("RGB", (512, 640), color=color).save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def make_wav(path: Path, seconds: float = 4.0, rate: int = 16000) -> Path:
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        silence = struct.pack("<h", 0)
        handle.writeframes(silence * frames)
    return path


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        settings = SimpleNamespace(characters_dir=root / "characters")
        settings.characters_dir.mkdir(parents=True, exist_ok=True)
        store = CharacterStore(settings)

        created = store.create(
            character_id="loc-main",
            name="Loc Tech",
            image_files=[
                make_image((20, 20, 20)),
                make_image((80, 80, 80)),
                make_image((140, 140, 140)),
            ],
            primary_index=1,
            voice="",
            persona="KOC tech tự nhiên",
        )

        assert created.character_id == "loc-main"
        assert created.reference_count == 3
        assert created.look_count == 0
        assert created.has_voice_clone is False
        assert len(created.reference_images) == 3
        assert store.get_master_image("loc-main").exists()
        assert store.get_render_image("loc-main").exists()

        look = store.add_look(
            character_id="loc-main",
            look_id="desk-gray",
            name="Desk Gray Tee",
            image_file=make_image((180, 180, 180)),
        )
        assert look.look_id == "desk-gray"
        assert look.image_url.endswith("/looks/desk-gray.png")
        assert store.get_render_image("loc-main", "desk-gray").exists()

        source_wav = make_wav(root / "source.wav", seconds=12.0)
        reference_wav = make_wav(root / "reference.wav", seconds=7.0)
        voice = store.set_voice_profile(
            "loc-main",
            source_wav=source_wav,
            reference_wav=reference_wav,
            reference_text="Chào mọi người, mình là Lộc và đây là đoạn giọng mẫu.",
            source_duration_sec=12.0,
            reference_duration_sec=7.0,
            name="Loc main voice",
        )
        assert voice.engine == "vieneu"
        assert voice.reference_audio_url.endswith("/voice/reference.wav")

        loaded = store.get("loc-main")
        assert loaded.look_count == 1
        assert len(loaded.looks) == 1
        assert loaded.looks[0].name == "Desk Gray Tee"
        assert loaded.has_voice_clone is True
        assert loaded.voice == "vieneu:clone"
        assert loaded.voice_clone is not None
        assert loaded.voice_clone.name == "Loc main voice"
        voice_ref = store.get_voice_reference("loc-main")
        assert voice_ref is not None
        assert voice_ref[0].exists()
        assert "mình là Lộc" in voice_ref[1]
        assert len(store.list_looks("loc-main")) == 1
        assert len(store.list()) == 1

    print("CharacterStore smoke test OK")


if __name__ == "__main__":
    main()
