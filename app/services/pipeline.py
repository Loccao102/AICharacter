import shutil
from pathlib import Path
from typing import Callable

from app.services.composer import VideoComposer, format_vnd
from app.services.musetalk import MuseTalkService
from app.services.tts import HybridTTSService
from app.settings import Settings


ProgressCallback = Callable[[int, str], None]


class RenderPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tts = HybridTTSService(settings)
        self.musetalk = MuseTalkService(settings)
        self.composer = VideoComposer(settings)

    @staticmethod
    def build_default_script(product_name: str, current_price: int, buy_price: int) -> str:
        return (
            f"Nếu mọi người đang để ý {product_name} thì xem giá trước nhé. "
            f"Hiện mình đang ghi nhận khoảng {format_vnd(current_price)}. "
            f"Nếu tài khoản của bạn ra {format_vnd(buy_price)} hoặc thấp hơn thì đây là mức giá đáng chú ý. "
            "Bấm vào sản phẩm để kiểm tra giá thực tế của tài khoản bạn nhé."
        )

    def render(
        self,
        job_id: str,
        character_image: Path,
        product_image: Path,
        product_name: str,
        current_price: int,
        buy_price: int,
        script: str | None,
        voice: str | None,
        voice_reference: Path | None,
        voice_reference_text: str,
        update: ProgressCallback,
    ) -> str:
        work_dir = self.settings.jobs_dir / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        script = (script or "").strip() or self.build_default_script(
            product_name,
            current_price,
            buy_price,
        )
        (work_dir / "script.txt").write_text(script, encoding="utf-8")

        audio_wav = work_dir / "speech.wav"
        subtitle_path = work_dir / "captions.srt"

        if voice_reference is not None:
            update(15, "Đang clone giọng bằng VieNeu-TTS local")
        else:
            update(15, "Đang tạo giọng nói bằng TTS local")

        engine = self.tts.synthesize(
            text=script,
            audio_wav=audio_wav,
            subtitle_path=subtitle_path,
            voice=voice,
            reference_audio=voice_reference,
            reference_text=voice_reference_text,
        )
        (work_dir / "tts-engine.txt").write_text(engine, encoding="utf-8")

        update(35, "Đang lip-sync nhân vật bằng MuseTalk")
        talking_video = self.musetalk.generate(
            character_image=character_image,
            audio_path=audio_wav,
            work_dir=work_dir,
        )

        update(85, "Đang ghép video 9:16, sản phẩm và subtitle")
        output_path = self.settings.outputs_dir / f"{job_id}.mp4"
        self.composer.compose(
            talking_video=talking_video,
            product_image=product_image,
            product_name=product_name,
            current_price=current_price,
            buy_price=buy_price,
            subtitle_path=subtitle_path,
            output_path=output_path,
            work_dir=work_dir,
        )

        for candidate in (work_dir / "musetalk_results",):
            if candidate.exists():
                shutil.rmtree(candidate, ignore_errors=True)

        update(98, "Đang hoàn tất")
        return f"/outputs/{job_id}.mp4"
