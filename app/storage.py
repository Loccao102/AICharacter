import json
import re
from pathlib import Path
from typing import BinaryIO

from PIL import Image

from app.schemas import CharacterInfo
from app.settings import Settings


_CHARACTER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}$")


class CharacterStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _dir(self, character_id: str) -> Path:
        return self.settings.characters_dir / character_id

    def _metadata_path(self, character_id: str) -> Path:
        return self._dir(character_id) / "character.json"

    def validate_id(self, character_id: str) -> str:
        value = character_id.strip().lower()
        if not _CHARACTER_ID.fullmatch(value):
            raise ValueError(
                "character_id chỉ gồm a-z, 0-9, '-' hoặc '_', dài 2-49 ký tự"
            )
        return value

    def create(self, character_id: str, name: str, image_file: BinaryIO) -> CharacterInfo:
        character_id = self.validate_id(character_id)
        character_dir = self._dir(character_id)
        if character_dir.exists():
            raise FileExistsError(f"Character '{character_id}' đã tồn tại")

        character_dir.mkdir(parents=True, exist_ok=False)
        image_path = character_dir / "master.png"

        with Image.open(image_file) as image:
            image = image.convert("RGB")
            max_side = 1600
            if max(image.size) > max_side:
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            image.save(image_path, "PNG", optimize=True)

        metadata = {
            "character_id": character_id,
            "name": name.strip() or character_id,
            "master_image": "master.png",
        }
        self._metadata_path(character_id).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.get(character_id)

    def get(self, character_id: str) -> CharacterInfo:
        metadata_path = self._metadata_path(character_id)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Không tìm thấy character '{character_id}'")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return CharacterInfo(
            character_id=metadata["character_id"],
            name=metadata["name"],
            image_url=f"/characters/{metadata['character_id']}/master.png",
        )

    def get_master_image(self, character_id: str) -> Path:
        self.get(character_id)
        return self._dir(character_id) / "master.png"

    def list(self) -> list[CharacterInfo]:
        result: list[CharacterInfo] = []
        for entry in sorted(self.settings.characters_dir.iterdir()):
            if not entry.is_dir():
                continue
            try:
                result.append(self.get(entry.name))
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                continue
        return result
