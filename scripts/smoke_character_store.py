from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys

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
            voice="vi-VN-NamMinhNeural",
            persona="KOC tech tự nhiên",
        )

        assert created.character_id == "loc-main"
        assert created.reference_count == 3
        assert created.voice == "vi-VN-NamMinhNeural"
        assert len(created.reference_images) == 3
        assert store.get_master_image("loc-main").exists()
        assert store.get_default_voice("loc-main") == "vi-VN-NamMinhNeural"
        assert len(store.list()) == 1

    print("CharacterStore smoke test OK")


if __name__ == "__main__":
    main()
