import json
import re
import shutil
from pathlib import Path
from typing import BinaryIO, Iterable

from PIL import Image

from app.schemas import CharacterInfo, CharacterLookInfo
from app.settings import Settings


_CHARACTER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}$")
_LOOK_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}$")
_MAX_REFERENCE_IMAGES = 5
_MAX_LOOKS = 24


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

    def validate_look_id(self, look_id: str) -> str:
        value = look_id.strip().lower()
        if not _LOOK_ID.fullmatch(value):
            raise ValueError("look_id chỉ gồm a-z, 0-9, '-' hoặc '_', dài 2-49 ký tự")
        return value

    @staticmethod
    def _save_normalized_image(image_file: BinaryIO, destination: Path) -> None:
        try:
            image_file.seek(0)
        except (AttributeError, OSError):
            pass

        with Image.open(image_file) as image:
            image = image.convert("RGB")
            max_side = 1600
            if max(image.size) > max_side:
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            if min(image.size) < 256:
                raise ValueError("Ảnh quá nhỏ, cần tối thiểu 256px mỗi chiều")
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, "PNG", optimize=True)

    def _read_metadata(self, character_id: str) -> dict:
        character_id = self.validate_id(character_id)
        metadata_path = self._metadata_path(character_id)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Không tìm thấy character '{character_id}'")
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def _write_metadata(self, character_id: str, metadata: dict) -> None:
        self._metadata_path(character_id).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create(
        self,
        character_id: str,
        name: str,
        image_files: Iterable[BinaryIO],
        *,
        primary_index: int = 0,
        voice: str = "",
        persona: str = "",
        source_type: str = "self_avatar",
    ) -> CharacterInfo:
        character_id = self.validate_id(character_id)
        character_dir = self._dir(character_id)
        if character_dir.exists():
            raise FileExistsError(f"Character '{character_id}' đã tồn tại")

        files = list(image_files)
        if not files:
            raise ValueError("Cần ít nhất 1 ảnh reference")
        if len(files) > _MAX_REFERENCE_IMAGES:
            raise ValueError(f"Tối đa {_MAX_REFERENCE_IMAGES} ảnh reference cho mỗi character")
        if primary_index < 0 or primary_index >= len(files):
            raise ValueError("primary_index không hợp lệ")

        character_dir.mkdir(parents=True, exist_ok=False)
        refs_dir = character_dir / "references"

        try:
            reference_names: list[str] = []
            for index, image_file in enumerate(files, start=1):
                filename = f"ref_{index:02d}.png"
                self._save_normalized_image(image_file, refs_dir / filename)
                reference_names.append(filename)

            master_source = refs_dir / reference_names[primary_index]
            shutil.copy2(master_source, character_dir / "master.png")

            metadata = {
                "character_id": character_id,
                "name": name.strip() or character_id,
                "master_image": "master.png",
                "voice": voice.strip(),
                "persona": persona.strip(),
                "source_type": source_type.strip() or "self_avatar",
                "references": reference_names,
                "primary_reference": reference_names[primary_index],
                "looks": [],
            }
            self._write_metadata(character_id, metadata)
        except Exception:
            shutil.rmtree(character_dir, ignore_errors=True)
            raise

        return self.get(character_id)

    def _look_info(self, character_id: str, item: dict) -> CharacterLookInfo:
        filename = item.get("filename") or f"{item['look_id']}.png"
        return CharacterLookInfo(
            look_id=item["look_id"],
            name=item.get("name") or item["look_id"],
            image_url=f"/characters/{character_id}/looks/{filename}",
            source_type=item.get("source_type", "upload"),
        )

    def get(self, character_id: str) -> CharacterInfo:
        metadata = self._read_metadata(character_id)
        reference_names = metadata.get("references") or []
        reference_urls = [
            f"/characters/{metadata['character_id']}/references/{name}"
            for name in reference_names
        ]

        # Backward compatible với character V1 chỉ có master.png.
        if not reference_urls:
            reference_urls = [f"/characters/{metadata['character_id']}/master.png"]

        looks = [
            self._look_info(metadata["character_id"], item)
            for item in metadata.get("looks", [])
            if item.get("look_id")
        ]

        return CharacterInfo(
            character_id=metadata["character_id"],
            name=metadata["name"],
            image_url=f"/characters/{metadata['character_id']}/{metadata.get('master_image', 'master.png')}",
            voice=metadata.get("voice", ""),
            persona=metadata.get("persona", ""),
            source_type=metadata.get("source_type", "self_avatar"),
            reference_images=reference_urls,
            reference_count=len(reference_urls),
            looks=looks,
            look_count=len(looks),
        )

    def add_look(
        self,
        character_id: str,
        look_id: str,
        name: str,
        image_file: BinaryIO,
        *,
        source_type: str = "upload",
    ) -> CharacterLookInfo:
        metadata = self._read_metadata(character_id)
        character_id = metadata["character_id"]
        look_id = self.validate_look_id(look_id)
        looks = list(metadata.get("looks") or [])

        if len(looks) >= _MAX_LOOKS:
            raise ValueError(f"Tối đa {_MAX_LOOKS} looks cho mỗi character")
        if any(item.get("look_id") == look_id for item in looks):
            raise FileExistsError(f"Look '{look_id}' đã tồn tại trong character '{character_id}'")

        filename = f"{look_id}.png"
        destination = self._dir(character_id) / "looks" / filename
        self._save_normalized_image(image_file, destination)

        item = {
            "look_id": look_id,
            "name": name.strip() or look_id,
            "filename": filename,
            "source_type": source_type.strip() or "upload",
        }
        looks.append(item)
        metadata["looks"] = looks
        self._write_metadata(character_id, metadata)
        return self._look_info(character_id, item)

    def list_looks(self, character_id: str) -> list[CharacterLookInfo]:
        return self.get(character_id).looks

    def get_master_image(self, character_id: str) -> Path:
        metadata = self._read_metadata(character_id)
        return self._dir(metadata["character_id"]) / metadata.get("master_image", "master.png")

    def get_render_image(self, character_id: str, look_id: str | None = None) -> Path:
        if not look_id:
            return self.get_master_image(character_id)

        metadata = self._read_metadata(character_id)
        normalized_look_id = self.validate_look_id(look_id)
        for item in metadata.get("looks", []):
            if item.get("look_id") == normalized_look_id:
                filename = item.get("filename") or f"{normalized_look_id}.png"
                path = self._dir(metadata["character_id"]) / "looks" / filename
                if not path.exists():
                    raise FileNotFoundError(
                        f"File của look '{normalized_look_id}' không tồn tại"
                    )
                return path
        raise FileNotFoundError(
            f"Không tìm thấy look '{normalized_look_id}' của character '{metadata['character_id']}'"
        )

    def get_default_voice(self, character_id: str) -> str:
        return self.get(character_id).voice

    def list(self) -> list[CharacterInfo]:
        result: list[CharacterInfo] = []
        for entry in sorted(self.settings.characters_dir.iterdir()):
            if not entry.is_dir():
                continue
            try:
                result.append(self.get(entry.name))
            except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
                continue
        return result
