# AICharacter

AICharacter là MVP local để biến **một identity cố định + nhiều Looks + nội dung sản phẩm** thành video dọc 9:16 có nhân vật nói tiếng Việt.

V2.1 tập trung vào workflow:

```text
1-5 ảnh cùng một người
      ↓
Persistent Character Profile
(character_id + master face + references + voice + persona)
      ↓
Multiple Looks
(hoodie / desk / standing / close-up / ...)
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

Mục tiêu là: **tạo character một lần, sau đó mọi video chỉ chọn lại `character_id` và tùy chọn `look_id`, thay vì sinh một người mới**.

Dự án ưu tiên chạy trên Windows có NVIDIA GPU. Với RTX 2060 6GB, nên bật FP16 và batch size nhỏ.

## V2.1 có gì

- Tạo character từ **1-5 ảnh reference** của cùng một người.
- Chọn một ảnh làm `master.png` cho MuseTalk.
- Lưu toàn bộ reference set để phục vụ identity-preserving generation sau này.
- Mỗi character có `character_id`, tên, voice mặc định và persona riêng.
- Thêm nhiều **Looks** cho cùng một character: outfit, background, pose, framing khác nhau.
- Generate video bằng `character_id + look_id`; nếu `look_id` trống thì dùng master face.
- Backward compatible với character V1 chỉ có một `master.png`.
- TTS tiếng Việt bằng `edge-tts`.
- Tạo subtitle SRT tự động.
- Gọi MuseTalk 1.5 local để lip-sync.
- Ghép talking-head + ảnh sản phẩm + current price + buy price thành video 9:16.
- Web UI local tại `http://127.0.0.1:8000`.
- Job API để render không khóa request.
- Script PowerShell để bootstrap môi trường Windows.

> V2.1 vẫn chưa cố làm “nhân vật cầm đúng sản phẩm”. Sản phẩm được hiển thị dưới dạng packshot/card để tránh AI làm sai logo, màu hoặc hình dáng sản phẩm.

## Kiến trúc

```text
Browser
  ↓
FastAPI
  ↓
Character Store
  ├── character.json
  ├── master.png
  ├── references/ref_01..05.png
  └── looks/
      ├── desk-gray.png
      ├── hoodie-dark.png
      └── ...
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

MuseTalk upstream hiện khuyến nghị Python 3.10, PyTorch 2.0.1 + CUDA 11.8. Với RTX 2060 6GB, V2.1 phù hợp để render batch nhưng không nên kỳ vọng realtime.

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

## Luồng dùng V2.1

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

### B. Thêm Multiple Looks

Một Look là một ảnh khác của **cùng identity**. Ví dụ:

```text
desk-gray     → áo thun xám, ngồi bàn
hoodie-dark   → hoodie tối màu
standing      → đứng nói
closeup       → khung cận mặt
```

UI lưu từng Look tại:

```text
data/characters/<character_id>/looks/<look_id>.png
```

Metadata character sẽ có thêm:

```json
{
  "looks": [
    {
      "look_id": "desk-gray",
      "name": "Desk Gray Tee",
      "filename": "desk-gray.png",
      "source_type": "upload"
    }
  ]
}
```

### C. Generate mọi video bằng cùng character

Sau khi character đã được tạo, các video tiếp theo dùng:

```text
character_id = loc-main
look_id      = desk-gray   # optional
```

Nếu `look_id` trống, hệ thống dùng `master.png`. Nếu có `look_id`, MuseTalk dùng ảnh của Look tương ứng nhưng character vẫn là cùng identity do bạn quản lý.

Bạn nhập thêm:

- ảnh sản phẩm;
- tên sản phẩm;
- giá hiện tại;
- `buy price`;
- script;
- voice override nếu muốn.

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

API cũ gửi một file tên `image` vẫn được hỗ trợ.

### Get character

```http
GET /api/characters/{character_id}
```

Response có `image_url`, `reference_images`, `reference_count`, `voice`, `persona`, `looks`, `look_count`.

### List Looks

```http
GET /api/characters/{character_id}/looks
```

### Add Look

```http
POST /api/characters/{character_id}/looks
Content-Type: multipart/form-data
```

Fields:

```text
look_id      required
name         required
image        required
```

### Generate video

```http
POST /api/videos
Content-Type: multipart/form-data
```

Fields:

```text
character_id
look_id (optional; empty = master face)
product_name
current_price
buy_price
product_image
script (optional)
voice (optional override)
```

Nếu `voice` trống, app dùng voice lưu trong character.

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

## Điều V2.1 đã làm và chưa làm

V2.1 giải quyết **persistent identity ở cấp ứng dụng**: một character có bộ reference, master face và nhiều Look riêng. Render có thể đổi Look mà không tạo một character record mới.

V2.1 **chưa tự sinh Look mới từ reference**. Hiện Look được upload thủ công. Bước tiếp theo là identity-preserving generation: đưa 3-5 reference vào model → sinh outfit/background/pose mới nhưng vẫn giữ đúng khuôn mặt.

## Roadmap

- [x] Persistent character registry
- [x] 1-5 face reference images / character
- [x] Master face selection
- [x] Character default voice + persona
- [x] Reuse same `character_id` across all videos
- [x] Multiple Looks storage + API + UI
- [x] Render video bằng `look_id`
- [x] Vietnamese TTS
- [x] Subtitle generation
- [x] MuseTalk adapter
- [x] 9:16 affiliate composer
- [x] Simple web UI
- [ ] Identity-preserving generator: references → new Look, same face
- [ ] ComfyUI adapter cho identity-preserving workflow
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
