# AICharacter

AICharacter là MVP local để biến **1 ảnh nhân vật cố định + nội dung sản phẩm** thành video dọc 9:16 có nhân vật nói tiếng Việt.

Mục tiêu V1:

```text
Character image
     +
Product image / giá
     +
Script
     ↓
Vietnamese TTS
     ↓
MuseTalk 1.5 lip-sync
     ↓
FFmpeg composer
     ↓
1080x1920 MP4
```

Dự án ưu tiên chạy trên máy Windows có NVIDIA GPU. Với cấu hình RTX 2060 6GB, nên bật FP16 và batch size nhỏ.

## V1 có gì

- Lưu nhiều character cố định.
- TTS tiếng Việt bằng `edge-tts` (không cần API key, cần Internet).
- Tạo subtitle SRT tự động.
- Gọi MuseTalk 1.5 local để lip-sync.
- Ghép talking-head + ảnh sản phẩm + current price + buy price thành video 9:16.
- Web UI đơn giản tại `http://127.0.0.1:8000`.
- Job API để render không khóa request.
- Script PowerShell để bootstrap môi trường Windows.

> V1 chưa cố làm “nhân vật cầm đúng sản phẩm”. Sản phẩm được hiển thị dưới dạng packshot/card để tránh AI làm sai logo, màu hoặc hình dáng sản phẩm.

## Kiến trúc

```text
Browser
  ↓
FastAPI
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

MuseTalk upstream hiện khuyến nghị Python 3.10, PyTorch 2.0.1 + CUDA 11.8 và có hướng dẫn Windows riêng. Upstream cũng đã test FP16 trên RTX 3050 Ti Laptop 4GB VRAM, nên RTX 2060 6GB phù hợp để thử V1 nhưng sẽ không realtime.

## Cài nhanh trên Windows

### 1. Clone AICharacter

```powershell
git clone https://github.com/Loccao102/AICharacter.git
cd AICharacter
```

### 2. Chạy bootstrap

Mở PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_windows.ps1
```

Script sẽ:

- tạo `.venv` cho API;
- cài dependency của AICharacter;
- clone MuseTalk vào `external/MuseTalk` nếu chưa có;
- tạo file `.env` từ `.env.example`.

### 3. Cài môi trường MuseTalk

MuseTalk có dependency GPU riêng. Chạy:

```powershell
.\scripts\setup_musetalk_windows.ps1
```

Sau đó tải model weights theo script chính thức của MuseTalk:

```powershell
cd external\MuseTalk
.\download_weights.bat
cd ..\..
```

### 4. Kiểm tra máy

```powershell
.\.venv\Scripts\python.exe scripts\verify_system.py
```

### 5. Chạy app

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Mở:

```text
http://127.0.0.1:8000
```

## Luồng dùng

### A. Tạo/import character

V1 nhận một ảnh chân dung làm master character. Ảnh nên:

- nhìn thẳng hoặc lệch rất nhẹ;
- mặt rõ, không bị che;
- từ ngực hoặc eo trở lên;
- ánh sáng đều;
- tối thiểu khoảng 768px;
- không dùng ảnh của người thật nếu bạn không có quyền sử dụng.

Upload ảnh tại UI. App lưu:

```text
data/characters/<character_id>/master.png
```

### B. Generate video

Nhập:

- character;
- ảnh sản phẩm;
- tên sản phẩm;
- giá hiện tại;
- `buy price`;
- script (hoặc để app tự tạo script template).

Ví dụ script:

```text
Nếu mọi người thấy con này xuống khoảng 299 nghìn hoặc thấp hơn thì mình thấy có thể chốt. Còn nếu vẫn trên 400 nghìn thì chưa cần vội. Bấm vào sản phẩm xem tài khoản của bạn đang ra giá bao nhiêu nhé.
```

App trả `job_id`. UI tự poll trạng thái và hiển thị video khi render xong.

## API

### Create character

```http
POST /api/characters
Content-Type: multipart/form-data
```

Fields:

```text
character_id
name
image
```

### Generate

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
voice (optional)
```

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

Nếu FFmpeg đã có trong PATH thì giữ `FFMPEG_BIN=ffmpeg` và có thể để `FFMPEG_DIR` trống.

## Vì sao V1 dùng Python thay vì Go?

Model inference của MuseTalk/PyTorch là Python-first. V1 giữ toàn bộ GPU worker trong Python để giảm số điểm lỗi. Khi pipeline đã chạy ổn, có thể thêm Go API/orchestrator phía trước mà không thay phần inference.

## Roadmap

- [x] Character registry
- [x] Vietnamese TTS
- [x] Subtitle generation
- [x] MuseTalk adapter
- [x] 9:16 affiliate composer
- [x] Simple web UI
- [ ] ComfyUI adapter: prompt → master character
- [ ] Local Vietnamese TTS provider
- [ ] LivePortrait motion layer
- [ ] Multiple Looks cho cùng character
- [ ] Product background removal
- [ ] LLM script generator
- [ ] Batch generate nhiều creative
- [ ] Queue Redis/Celery cho production
- [ ] Analytics / affiliate integration

## Lưu ý license

Repo này chỉ là orchestration code. MuseTalk, Edge TTS, model weights và các dependency khác có license/điều khoản riêng. Nếu dùng thương mại, hãy kiểm tra license của từng model/dependency trước khi triển khai production.
