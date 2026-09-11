# AICharacter

AICharacter là hệ thống local để tạo video dọc 9:16 từ **một identity cố định + nhiều Looks + Voice Identity riêng + nội dung sản phẩm**.

V2.2 chuyển TTS mặc định sang **VieNeu-TTS v3 Turbo chạy local bằng ONNX/CPU**, còn MuseTalk dùng RTX để lip-sync.

```text
1-5 ảnh cùng một người
      ↓
Persistent Character Profile
(character_id + master face + references + persona)
      ↓
Multiple Looks
      ↓
Voice Identity
(source audio → 3-8s reference → VieNeu local clone)
      ↓
Product + giá + script
      ↓
VieNeu-TTS → speech.wav
      ↓
MuseTalk 1.5 → talking.mp4
      ↓
FFmpeg composer → 1080x1920 MP4
```

## V2.2 có gì

- 1–5 face references / character.
- Chọn master face cho MuseTalk.
- Multiple Looks: hoodie, desk, standing, close-up...
- **Voice Identity local** bằng VieNeu-TTS v3 Turbo.
- Upload audio giọng thật; app lưu source đầy đủ và tạo reference tối đa 8 giây.
- Mỗi character có thể tự dùng voice clone của chính nó.
- VieNeu chạy trong virtual environment riêng, không tranh dependency với MuseTalk.
- VieNeu dùng ONNX/CPU; MuseTalk dùng CUDA/GPU.
- Edge TTS chỉ còn là fallback tương thích khi override rõ ràng.
- Subtitle SRT được tạo tự động.
- FastAPI + web UI local tại `http://127.0.0.1:8000`.

## Kiến trúc

```text
Browser
  ↓
FastAPI
  ↓
Character Store
  ├── character.json
  ├── master.png
  ├── references/
  ├── looks/
  └── voice/
      ├── source.wav
      └── reference.wav
  ↓
Render Pipeline
  ├── VieNeu-TTS v3 Turbo (CPU / ONNX)
  ├── MuseTalk 1.5 (RTX / CUDA)
  └── FFmpeg + Pillow
```

Các model/runtime lớn nằm ngoài git trong `external/`.

## Yêu cầu

- Windows 10/11 64-bit
- Python 3.10
- NVIDIA GPU + driver
- FFmpeg trong `PATH`
- Git
- đủ dung lượng cho MuseTalk + VieNeu model cache

## Setup Windows

```powershell
git clone https://github.com/Loccao102/AICharacter.git
cd AICharacter
Set-ExecutionPolicy -Scope Process Bypass

.\scripts\setup_windows.ps1
.\scripts\setup_musetalk_windows.ps1
.\scripts\download_musetalk_weights.ps1
.\scripts\setup_vieneu_windows.ps1
```

`setup_vieneu_windows.ps1` tạo môi trường riêng tại:

```text
external/vieneu/.venv
```

và cài:

```text
vieneu==3.6.4
```

sau đó khởi tạo backend `onnx` để model cần thiết được tải/cache trước.

Kiểm tra toàn bộ:

```powershell
.\.venv\Scripts\python.exe scripts\verify_system.py
```

Khi mọi thứ ổn:

```text
OK: MuseTalk 1.5 + CUDA + VieNeu local voice engine are ready.
```

Chạy app:

```powershell
.\scripts\run.ps1
```

Mở:

```text
http://127.0.0.1:8000
```

## Character Identity

Upload 1–5 ảnh cùng một người. Khuyến nghị có:

- chính diện;
- nghiêng trái/phải nhẹ;
- biểu cảm tự nhiên;
- ít nhất một ảnh từ ngực trở lên;
- mặt rõ, ánh sáng đều.

Dữ liệu được lưu:

```text
data/characters/<character_id>/
├── character.json
├── master.png
├── references/
└── looks/
```

## Voice Identity

Trong UI chọn character → upload audio giọng của chính bạn.

V1 của Voice Identity xử lý như sau:

```text
voice upload (3 giây → 5 phút)
        ↓
normalize mono 16 kHz
        ↓
remove leading silence
        ↓
first voiced window, max 8 giây
        ↓
reference.wav
        ↓
VieNeu-TTS v3 Turbo
```

App vẫn giữ cả source dài tại:

```text
data/characters/<character_id>/voice/source.wav
```

và đoạn clone tại:

```text
data/characters/<character_id>/voice/reference.wav
```

### Quan trọng về transcript

VieNeu cần transcript khớp với đoạn reference. Vì V2.2 tự lấy **đoạn đầu có tiếng, tối đa 8 giây**, phần `reference_text` trong UI phải là chính nội dung bạn nói ở đoạn đó.

Cách dễ nhất để test đầu tiên là thu riêng một clip 5–8 giây, ví dụ:

```text
Chào mọi người, mình là Lộc và hôm nay mình sẽ thử một cách làm video mới.
```

Khi Voice Identity đã lưu, render video để trống `Override Voice` sẽ tự dùng clone đó.

## Voice override

Các giá trị hỗ trợ:

```text
để trống             → voice clone của character nếu có
vieneu:clone          → ép dùng clone
vieneu:<preset-id>    → dùng preset VieNeu
edge:<voice-name>     → Edge TTS compatibility fallback
```

Ví dụ:

```text
edge:vi-VN-NamMinhNeural
```

Edge TTS không còn là engine mặc định vì endpoint consumer có thể trả 403.

## API

### Tạo character

```http
POST /api/characters
```

Multipart fields:

```text
character_id
name
images            1-5 files
primary_index
voice             optional
persona           optional
```

### Thêm Look

```http
POST /api/characters/{character_id}/looks
```

```text
look_id
name
image
```

### Tạo / thay Voice Identity

```http
POST /api/characters/{character_id}/voice
Content-Type: multipart/form-data
```

Fields:

```text
audio             required
reference_text    required
name              optional
```

### Generate video

```http
POST /api/videos
```

```text
character_id
look_id            optional
product_name
current_price
buy_price
product_image
script              optional
voice               optional override
```

### Job status

```http
GET /api/jobs/{job_id}
```

## `.env`

```env
MUSETALK_DIR=external/MuseTalk
MUSETALK_PYTHON=external/MuseTalk/.venv/Scripts/python.exe
MUSETALK_RESULT_DIR=results/aicharacter

VIENEU_PYTHON=external/vieneu/.venv/Scripts/python.exe
VIENEU_BACKEND=onnx
VIENEU_PRESET_VOICE=
VIENEU_TIMEOUT_SEC=900

FFMPEG_BIN=ffmpeg
GPU_BATCH_SIZE=2
USE_FP16=true
MAX_GPU_WORKERS=1
```

## Vì sao VieNeu chạy riêng bằng CPU

Máy có RTX 2060 6GB sẽ hợp lý hơn khi:

```text
CPU → VieNeu voice synthesis
GPU → MuseTalk lip-sync
```

thay vì để TTS chiếm thêm VRAM trước khi MuseTalk render.

VieNeu upstream mô tả v3 Turbo là 48 kHz, hỗ trợ instant voice cloning từ clip ngắn và có backend ONNX/CPU. AICharacter dùng runtime riêng để tránh xung đột với stack PyTorch 2.0.1/CUDA 11.8 của MuseTalk.

## Roadmap

- [x] Persistent character registry
- [x] 1–5 face references
- [x] Master face selection
- [x] Multiple Looks
- [x] Render by `look_id`
- [x] MuseTalk 1.5 local
- [x] Local VieNeu-TTS provider
- [x] Character Voice Identity
- [x] Keep long source audio + short clone reference
- [x] Edge TTS explicit fallback
- [x] Subtitle generation
- [x] 9:16 affiliate composer
- [ ] Tự VAD + chọn nhiều reference tốt nhất từ recording dài
- [ ] Tự transcript đoạn reference
- [ ] 3 voice styles: neutral / energetic / soft
- [ ] LoRA fine-tune từ 10–30 phút audio
- [ ] Identity-preserving image generation
- [ ] LivePortrait motion layer
- [ ] Product URL → scrape → script → video
- [ ] Batch generation / queue production

## License & consent

Repo này là orchestration code. MuseTalk, VieNeu-TTS, Edge TTS và model weights có license/điều khoản riêng; hãy kiểm tra upstream trước khi triển khai production thương mại.

Chỉ clone khuôn mặt hoặc giọng nói của chính bạn, hoặc của người đã cho phép rõ ràng.
