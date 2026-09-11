import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.settings import Settings


class ComposeError(RuntimeError):
    pass


def format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + "đ"


class VideoComposer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = []
        if bold:
            candidates.extend([
                Path("C:/Windows/Fonts/arialbd.ttf"),
                Path("C:/Windows/Fonts/segoeuib.ttf"),
            ])
        else:
            candidates.extend([
                Path("C:/Windows/Fonts/arial.ttf"),
                Path("C:/Windows/Fonts/segoeui.ttf"),
            ])
        candidates.extend([
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        ])
        for path in candidates:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        return ImageFont.load_default()

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return []
        lines: list[str] = []
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if width <= max_width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
        return lines

    def _build_panel(
        self,
        product_image: Path,
        product_name: str,
        current_price: int,
        buy_price: int,
        output: Path,
    ) -> None:
        width = self.settings.output_width
        height = self.settings.output_height - self.settings.talking_height
        panel = Image.new("RGB", (width, height), (14, 17, 23))
        draw = ImageDraw.Draw(panel)

        image_box = (48, 64, 360, 376)
        with Image.open(product_image) as product:
            product = product.convert("RGB")
            product = ImageOps.contain(
                product,
                (image_box[2] - image_box[0], image_box[3] - image_box[1]),
                Image.Resampling.LANCZOS,
            )
            card = Image.new("RGB", (336, 336), (245, 245, 245))
            x = (card.width - product.width) // 2
            y = (card.height - product.height) // 2
            card.paste(product, (x, y))
            panel.paste(card, (36, 52))

        small = self._font(34)
        body = self._font(42)
        body_bold = self._font(44, bold=True)
        price_font = self._font(68, bold=True)
        buy_font = self._font(62, bold=True)

        text_x = 410
        max_text_width = width - text_x - 50
        name_lines = self._wrap(draw, product_name, body_bold, max_text_width)[:3]
        y = 62
        for line in name_lines:
            draw.text((text_x, y), line, font=body_bold, fill=(245, 247, 250))
            y += 56

        y += 18
        draw.text((text_x, y), "Giá hiện tại", font=small, fill=(170, 177, 190))
        y += 42
        draw.text((text_x, y), format_vnd(current_price), font=price_font, fill=(245, 247, 250))

        buy_y = 430
        draw.rounded_rectangle(
            (36, buy_y, width - 36, height - 42),
            radius=28,
            fill=(245, 247, 250),
        )
        draw.text((72, buy_y + 34), "MỨC GIÁ ĐÁNG CHÚ Ý", font=small, fill=(55, 60, 70))
        draw.text(
            (72, buy_y + 92),
            f"≤ {format_vnd(buy_price)}",
            font=buy_font,
            fill=(16, 18, 23),
        )
        cta = "Bấm vào sản phẩm để kiểm tra giá tài khoản của bạn"
        cta_lines = self._wrap(draw, cta, body, width - 500)
        cta_y = buy_y + 78
        for line in cta_lines[:2]:
            draw.text((500, cta_y), line, font=body, fill=(55, 60, 70))
            cta_y += 52

        panel.save(output, "PNG", optimize=True)

    def _run(self, command: list[str], cwd: Path, log_path: Path) -> subprocess.CompletedProcess:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\n\nSTDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}",
            encoding="utf-8",
        )
        return completed

    def compose(
        self,
        talking_video: Path,
        product_image: Path,
        product_name: str,
        current_price: int,
        buy_price: int,
        subtitle_path: Path,
        output_path: Path,
        work_dir: Path,
    ) -> Path:
        ffmpeg = self.settings.ffmpeg_bin
        if ffmpeg == "ffmpeg" and shutil.which("ffmpeg") is None:
            raise ComposeError("Không tìm thấy ffmpeg trong PATH")

        panel_path = work_dir / "product_panel.png"
        self._build_panel(
            product_image=product_image,
            product_name=product_name,
            current_price=current_price,
            buy_price=buy_price,
            output=panel_path,
        )

        width = self.settings.output_width
        talking_height = self.settings.talking_height
        panel_height = self.settings.output_height - talking_height

        base_filter = (
            f"[0:v]scale={width}:{talking_height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{talking_height}:(ow-iw)/2:(oh-ih)/2:color=0x0b0d12[v0];"
            f"[1:v]scale={width}:{panel_height}[panel];"
            "[v0][panel]vstack=inputs=2[base]"
        )
        subtitle_filter = (
            ";[base]subtitles=captions.srt:"
            "force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=740'[v]"
        )

        command = [
            ffmpeg,
            "-y",
            "-i",
            str(talking_video.resolve()),
            "-loop",
            "1",
            "-i",
            str(panel_path.resolve()),
            "-filter_complex",
            base_filter + subtitle_filter,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path.resolve()),
        ]
        log_path = work_dir / "ffmpeg.log"
        completed = self._run(command, work_dir, log_path)

        # Một số FFmpeg build không có libass/subtitles filter. Vẫn tạo video nếu gặp case đó.
        if completed.returncode != 0:
            fallback_filter = base_filter + ";[base]null[v]"
            fallback = command.copy()
            filter_index = fallback.index("-filter_complex") + 1
            fallback[filter_index] = fallback_filter
            completed = self._run(fallback, work_dir, log_path)

        if completed.returncode != 0 or not output_path.exists():
            raise ComposeError(f"FFmpeg compose thất bại. Xem log: {log_path}")
        return output_path
