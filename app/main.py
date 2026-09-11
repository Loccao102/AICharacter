from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from app.job_manager import JobManager
from app.schemas import CharacterInfo, CharacterLookInfo, JobInfo, VoiceProfileInfo
from app.services.pipeline import RenderPipeline
from app.services.voice_profile import VoiceReferencePreparer
from app.settings import get_settings
from app.storage import CharacterStore


settings = get_settings()
store = CharacterStore(settings)
jobs = JobManager(max_workers=settings.max_gpu_workers)
pipeline = RenderPipeline(settings)
voice_preparer = VoiceReferencePreparer(settings)

app = FastAPI(title="AICharacter", version="0.4.0")
app.mount("/outputs", StaticFiles(directory=settings.outputs_dir), name="outputs")
app.mount("/characters", StaticFiles(directory=settings.characters_dir), name="characters")


def _save_product_image(upload: UploadFile, destination: Path) -> None:
    try:
        with Image.open(upload.file) as image:
            image = image.convert("RGB")
            max_side = 1600
            if max(image.size) > max_side:
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            image.save(destination, "PNG", optimize=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Ảnh sản phẩm không hợp lệ: {exc}") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(settings.web_dir / "index.html")


@app.get("/api/health")
def health() -> dict:
    root = settings.musetalk_dir.resolve()
    return {
        "ok": True,
        "version": app.version,
        "musetalk_dir": str(root),
        "musetalk_cloned": (root / "scripts" / "inference.py").exists(),
        "musetalk_weights": (root / "models" / "musetalkV15" / "unet.pth").exists(),
        "musetalk_python": str(settings.musetalk_python),
        "musetalk_python_exists": settings.musetalk_python.exists(),
        "vieneu_python": str(settings.vieneu_python),
        "vieneu_python_exists": settings.vieneu_python.exists(),
        "vieneu_backend": settings.vieneu_backend,
        "ffmpeg": settings.ffmpeg_bin,
        "fp16": settings.use_fp16,
        "batch_size": settings.gpu_batch_size,
    }


@app.get("/api/characters", response_model=list[CharacterInfo])
def list_characters() -> list[CharacterInfo]:
    return store.list()


@app.get("/api/characters/{character_id}", response_model=CharacterInfo)
def get_character(character_id: str) -> CharacterInfo:
    try:
        return store.get(character_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/characters", response_model=CharacterInfo)
def create_character(
    character_id: str = Form(...),
    name: str = Form(...),
    voice: str = Form(""),
    persona: str = Form(""),
    primary_index: int = Form(0),
    images: list[UploadFile] | None = File(None),
    image: UploadFile | None = File(None),
) -> CharacterInfo:
    uploads = list(images or [])
    if not uploads and image is not None:
        uploads = [image]
    if not uploads:
        raise HTTPException(status_code=400, detail="Cần upload ít nhất 1 ảnh khuôn mặt")
    if len(uploads) > 5:
        raise HTTPException(status_code=400, detail="Tối đa 5 ảnh reference")

    try:
        return store.create(
            character_id=character_id,
            name=name,
            image_files=[upload.file for upload in uploads],
            primary_index=primary_index,
            voice=voice,
            persona=persona,
            source_type="self_avatar",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Không thể lưu character: {exc}") from exc


@app.get(
    "/api/characters/{character_id}/looks",
    response_model=list[CharacterLookInfo],
)
def list_character_looks(character_id: str) -> list[CharacterLookInfo]:
    try:
        return store.list_looks(character_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/characters/{character_id}/looks",
    response_model=CharacterLookInfo,
)
def create_character_look(
    character_id: str,
    look_id: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(...),
) -> CharacterLookInfo:
    try:
        return store.add_look(
            character_id=character_id,
            look_id=look_id,
            name=name,
            image_file=image.file,
            source_type="upload",
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Không thể lưu look: {exc}") from exc


@app.post(
    "/api/characters/{character_id}/voice",
    response_model=VoiceProfileInfo,
)
def create_character_voice(
    character_id: str,
    audio: UploadFile = File(...),
    reference_text: str = Form(...),
    name: str = Form("Main voice"),
) -> VoiceProfileInfo:
    transcript = reference_text.strip()
    if len(transcript) < 3:
        raise HTTPException(
            status_code=400,
            detail="Cần transcript đúng với đoạn reference 3–8 giây để clone giọng ổn định",
        )

    try:
        store.get(character_id)
        with TemporaryDirectory(prefix="aicharacter-voice-") as temp:
            prepared = voice_preparer.prepare(
                input_file=audio.file,
                original_name=audio.filename or "voice.wav",
                work_dir=Path(temp),
            )
            return store.set_voice_profile(
                character_id,
                source_wav=prepared.source_wav,
                reference_wav=prepared.reference_wav,
                reference_text=transcript,
                source_duration_sec=prepared.source_duration_sec,
                reference_duration_sec=prepared.reference_duration_sec,
                name=name,
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Không thể tạo voice profile: {exc}") from exc


@app.post("/api/videos", response_model=JobInfo)
def create_video(
    character_id: str = Form(...),
    product_name: str = Form(...),
    current_price: int = Form(...),
    buy_price: int = Form(...),
    product_image: UploadFile = File(...),
    script: str = Form(""),
    voice: str = Form(""),
    look_id: str = Form(""),
) -> JobInfo:
    if current_price <= 0 or buy_price <= 0:
        raise HTTPException(status_code=400, detail="Giá phải lớn hơn 0")
    if not product_name.strip():
        raise HTTPException(status_code=400, detail="Tên sản phẩm không được trống")

    try:
        character = store.get(character_id)
        character_image = store.get_render_image(character_id, look_id.strip() or None)
        stored_voice_reference = store.get_voice_reference(character_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    override_voice = voice.strip()
    selected_voice = override_voice or character.voice.strip() or None
    voice_reference: Path | None = None
    voice_reference_text = ""

    # Clone is the default when a character owns a local voice profile. A concrete
    # override such as vieneu:<preset> or edge:<voice> intentionally bypasses it.
    wants_clone = not override_voice or override_voice == "vieneu:clone"
    if wants_clone and stored_voice_reference is not None:
        voice_reference, voice_reference_text = stored_voice_reference
        selected_voice = "vieneu:clone"
    elif override_voice == "vieneu:clone" and stored_voice_reference is None:
        raise HTTPException(status_code=400, detail="Character chưa có voice clone")

    job_id = uuid4().hex
    work_dir = settings.jobs_dir / job_id
    work_dir.mkdir(parents=True, exist_ok=False)
    product_path = work_dir / "product.png"
    _save_product_image(product_image, product_path)

    job = jobs.create(job_id)

    def task(task_job_id: str, update) -> str:
        return pipeline.render(
            job_id=task_job_id,
            character_image=character_image,
            product_image=product_path,
            product_name=product_name.strip(),
            current_price=current_price,
            buy_price=buy_price,
            script=script,
            voice=selected_voice,
            voice_reference=voice_reference,
            voice_reference_text=voice_reference_text,
            update=update,
        )

    jobs.start(job_id, task)
    return job


@app.get("/api/jobs/{job_id}", response_model=JobInfo)
def get_job(job_id: str) -> JobInfo:
    try:
        return jobs.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
