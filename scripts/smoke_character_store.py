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
        assert created.look_count == 0
        assert created.voice == "vi-VN-NamMinhNeural"
        assert len(created.reference_images) == 3
        assert store.get_master_image("loc-main").exists()
        assert store.get_render_image("loc-main").exists()
        assert store.get_default_voice("loc-main") == "vi-VN-NamMinhNeural"

        look = store.add_look(
            character_id="loc-main",
            look_id="desk-gray",
            name="Desk Gray Tee",
            image_file=make_image((180, 180, 180)),
        )
        assert look.look_id == "desk-gray"
        assert look.image_url.endswith("/looks/desk-gray.png")
        assert store.get_render_image("loc-main", "desk-gray").exists()

        loaded = store.get("loc-main")
        assert loaded.look_count == 1
        assert len(loaded.looks) == 1
        assert loaded.looks[0].name == "Desk Gray Tee"
        assert len(store.list_looks("loc-main")) == 1
        assert len(store.list()) == 1

    print("CharacterStore smoke test OK")


if __name__ == "__main__":
    main()
