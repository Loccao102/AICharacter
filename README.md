# AICharacter

AICharacter là MVP local để biến **một identity cố định + nội dung sản phẩm** thành video dọc 9:16 có nhân vật nói tiếng Việt.

V2 tập trung vào workflow:

```text
1-5 ảnh cùng một người
      ↓
Persistent Character Profile
(character_id + master face + references + voice + persona)
      ↓
Product image / giá / script
      ↓
Vietnamese TTS
      ↓
MuseTalk 1.5 lip-sync
      ↓
FFmpeg composer
      ↓
1080x1920 MP4
```

Mục tiêu là: **tạo character một lần, sau đó mọi video chỉ chọn lại `character_id` đó thay vì sinh một người mới**.

Dự án ưu tiên chạy trên Windows có NVIDIA GPU. Với RTX 2060 6GB, nên bật FP16 và batch size nhỏ.

## V2 có gì

- Tạo character từ **1-5 ảnh reference** của cùng một người.
- Chọn một ảnh làm `master.png` cho MuseTalk hiện tại.
- Lưu toàn bộ reference set để dùng cho Multiple Looks / identity-preserving generation ở roadmap tiếp theo.
- Mỗi character có `character_id`, tên, voice mặc định và persona riêng.
- Generate video chỉ cần chọn character đã lưu; hệ thống dùng lại đúng master face + voice của character.
- Backward compatible với character V1 chỉ có một `master.png`.
- TTS tiếng Việt bằng `edge-tts` (không cần API key, cần Internet).
- Tạo subtitle SRT tự động.
- Gọi MuseTalk 1.5 local để lip-sync.
- Ghép talking-head + ảnh sản phẩm + current price + buy price thành video 9:16.
- Web UI local tại `http://127.0.0.1:8000`.
- Job API để render không khóa request.
- Script PowerShell để bootstrap môi trường Windows.

> V2 vẫn chưa cố làm “nhân vật cầm đúng sản phẩm”. Sản phẩm được hiển thị dưới dạng packshot/card để tránh AI làm sai logo, màu hoặc hình dáng sản phẩm.

## Kiến trúc

```text
Browser
  ↓
FastAPI
  ↓
Character Store
  ├── character.json
  ├── master.png
  └── references/ref_01..05.png
  ↓
Job Manager (1 GPU job/lần)
  ├── Edge TTS → speech.mp3 + captions.srt
  ├── MuseTalk 1.5 → talking.mp4
  └── FFmpeg + Pillow → final.mp4
```

MuseTalk được giữ ở thư mục `external/MuseTalk` và **không copy source/model vào repo này**.

## Yêu cầu

- Windows 10/11 64-bit
- Python 3.10
- NVIDIA GPU + driver
- FFmpeg trong `PATH`
- Git
- Khoảng trống ổ đĩa cho MuseTalk model weights

MuseTalk upstream hiện khuyến nghị Python 3.10, PyTorch 2.0.1 + CUDA 11.8 và có hướng dẫn Windows riêng. Upstream cũng đã test FP16 trên RTX 3050 Ti Laptop 4GB VRAM, nên RTX 2060 6GB phù hợp để thử V2 nhưng sẽ không realtime.

## Cài nhanh trên Windows

```powershell
git clone https://github.com/Loccao102/AICharacter.git
cd AICharacter
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
.\scripts\setup_musetalk_windows.ps1
```

Tải model weights:

```powershell
cd external\MuseTalk
.\download_weights.bat
cd ..\..
```

Kiểm tra máy:

```powershell
.\.venv\Scripts\python.exe scripts\verify_system.py
```

Chạy app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở `http://127.0.0.1:8000`.

## Luồng dùng V2

### A. Tạo character từ khuôn mặt của bạn

Upload 1-5 ảnh của **cùng một người**. Khuyến nghị:

- một ảnh chính diện từ ngực/eo trở lên;
- thêm góc nghiêng nhẹ trái/phải nếu có;
- mặt rõ, không bị che;
- ánh sáng đều;
- tối thiểu 256px mỗi chiều, nên dùng 768px trở lên;
- chỉ dùng khuôn mặt mà bạn có quyền sử dụng.

Trong UI, click một thumbnail để chọn ảnh `MASTER`. App lưu:

```text
data/characters/<character_id>/
├── character.json
├── master.png
└── references/
    ├── ref_01.png
    ├── ref_02.png
    └── ... ref_05.png
```

Ví dụ metadata:

```json
{
  "character_id": "loc-main",
  "name": "Loc Tech",
  "master_image": "master.png",
  "voice": "vi-VN-NamMinhNeural",
  "persona": "KOC tech tự nhiên, ngắn, tập trung vào giá",
  "source_type": "self_avatar",
  "references": ["ref_01.png", "ref_02.png", "ref_03.png"],
  "primary_reference": "ref_01.png"
}
```

### B. Generate mọi video bằng cùng character

Sau khi character đã được tạo, các video tiếp theo chỉ cần:

```text
character_id = loc-main
```

Bạn nhập thêm:

- ảnh sản phẩm;
- tên sản phẩm;
- giá hiện tại;
- `buy price`;
- script (hoặc để app tự tạo template);
- voice override nếu muốn, nếu để trống app dùng voice đã lưu của character.

Hệ thống **không tạo một khuôn mặt mới cho mỗi video**. Với V2, MuseTalk luôn render từ `master.png` của character đã chọn.

## API

### Create reusable character

```http
POST /api/characters
Content-Type: multipart/form-data
```

Fields:

```text
character_id      required
name              required
images            1-5 files, cùng field name
primary_index     optional, default 0
voice             optional
persona           optional
```

API cũ gửi một file tên `image` vẫn được hỗ trợ để giữ backward compatibility.

### Get character

```http
GET /api/characters/{character_id}
```

Response có `image_url`, `reference_images`, `reference_count`, `voice`, `persona`.

### Generate video

```http
POST /api/videos
Content-Type: multipart/form-data
```

Fields:

```text
character_id
product_name
current_price
buy_price
product_image
script (optional)
voice (optional override)
```

Nếu `voice` trống, app tự dùng voice lưu trong character.

### Job status

```http
GET /api/jobs/{job_id}
```

## Cấu hình `.env`

```env
MUSETALK_DIR=external/MuseTalk
MUSETALK_PYTHON=external/MuseTalk/.venv/Scripts/python.exe
FFMPEG_BIN=ffmpeg
FFMPEG_DIR=
EDGE_TTS_VOICE=vi-VN-NamMinhNeural
GPU_BATCH_SIZE=2
USE_FP16=true
```

## Điều V2 đã làm và chưa làm

V2 giải quyết **persistent identity** ở cấp ứng dụng: một character có bộ reference riêng và mọi video tái sử dụng đúng master face đó.

V2 **chưa** dùng 5 ảnh reference để sinh ra ảnh mới ở nhiều outfit/góc/bối cảnh mà vẫn giữ khuôn mặt. Đó là bước identity-preserving generation tiếp theo. Các reference đã được lưu sẵn để không phải thay đổi data model khi bổ sung tính năng đó.

## Vì sao dùng Python thay vì Go ở phần inference?

MuseTalk/PyTorch là Python-first. Giữ GPU worker trong Python làm MVP dễ ổn định hơn. Khi pipeline chạy ổn, có thể thêm Go API/orchestrator phía trước mà không thay phần inference.

## Roadmap

- [x] Persistent character registry
- [x] 1-5 face reference images / character
- [x] Master face selection
- [x] Character default voice + persona
- [x] Reuse same `character_id` across all videos
- [x] Vietnamese TTS
- [x] Subtitle generation
- [x] MuseTalk adapter
- [x] 9:16 affiliate composer
- [x] Simple web UI
- [ ] Identity-preserving generator: references → new Look, same face
- [ ] Multiple Looks (outfit/background/pose) cho cùng character
- [ ] ComfyUI adapter
- [ ] Local Vietnamese TTS provider
- [ ] LivePortrait motion layer
- [ ] Product background removal
- [ ] LLM script generator sử dụng `persona`
- [ ] Batch generate nhiều creative
- [ ] Queue Redis/Celery cho production
- [ ] Analytics / affiliate integration

## Lưu ý license & consent

Repo này chỉ là orchestration code. MuseTalk, Edge TTS, model weights và các dependency khác có license/điều khoản riêng. Nếu dùng thương mại, hãy kiểm tra license của từng model/dependency trước khi triển khai production.

Nếu dùng khuôn mặt của người thật, chỉ sử dụng hình ảnh của chính bạn hoặc người đã đồng ý rõ ràng cho việc tạo avatar/video AI.
