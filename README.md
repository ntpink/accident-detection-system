# Traffic Accident Detection System 🚗💥
**Hệ thống Phát hiện và Cảnh báo Tai nạn Giao thông qua Video ứng dụng Trí tuệ Nhân tạo**

Dự án bài tập lớn xây dựng ứng dụng web hoàn chỉnh: cho phép người dùng tải lên video giao thông, mô hình AI chạy phân tích trước ở chế độ nền (Background Worker), sau đó hệ thống phát lại video gốc chất lượng cao kèm các bounding box bám xe mượt mà và cảnh báo tai nạn trực quan.

---

## 📌 1. Các Tính Năng & Phạm Vi Dự Án

- **Xử lý Video Tải Lên:** Hỗ trợ các định dạng video giao thông phổ biến (`.mp4`, `.avi`, `.mov`, `.mkv`), dung lượng tối đa cấu hình được (mặc định 500MB). Tự động chuẩn hóa codec về H.264 qua FFmpeg để trình duyệt phát mượt mà.
- **Mô Hình AI Kép Hiện Đại:**
  1. **YOLO11x (Model chính):** Sử dụng trọng số `epoch61.pt` huấn luyện chuyên biệt cho bài toán tai nạn giao thông (tải từ Hugging Face `Enos-123/traffic-accident-detection-yolo11x`). Tự động phát hiện chỉ số lớp `accident` theo tên động. Chạy cách quãng mỗi $N$ frame ($N=3$) với `imgsz=640`.
  2. **YOLO11n + ByteTrack (Model theo dõi):** Chạy trên toàn bộ các frame để nhận diện các loại phương tiện (`car`, `motorcycle`, `bus`, `truck`) và gán mã định danh duy nhất (`track_id`) cho từng phương tiện.
- **Xử Lý Chuỗi Thời Gian (Temporal Processing):**
  - Lọc nhiễu qua số phát hiện liên tiếp tối thiểu (`MIN_CONSECUTIVE_DETECTIONS = 3`).
  - Tự động gộp các phát hiện cách nhau dưới 3 giây (`EVENT_MERGE_GAP_SECONDS = 3.0`) thành một sự kiện tai nạn hoàn chỉnh.
  - Lưu ảnh bằng chứng ở độ phân giải gốc với chất lượng JPEG 95 tại frame có độ tin cậy cao nhất (`peak_time`), có vẽ box và nhãn xe liên quan (IoU > 0).
- **Phát Lại Video & Canvas Overlay Độc Quyền:**
  - Không vẽ đè lên file video để tránh giảm độ nét gốc; video phát qua HTTP Range stream (RFC 7233).
  - Khung nhận diện được vẽ bằng thẻ Canvas HTML5 phủ chính xác lên trên, đồng bộ từng khung hình bằng `video.requestVideoFrameCallback` (fallback `requestAnimationFrame`).
  - Thuật toán **Nội suy tuyến tính (Linear Interpolation)** kết hợp **Làm mượt EMA (Exponential Moving Average)** giúp box di chuyển mượt mà, bám chắc theo xe, không rung giật.
  - Tự động tính toán scale và bù trừ phần viền đen letterbox (`object-fit: contain`) khi đổi kích thước cửa sổ hoặc xem Fullscreen.
  - Hỗ trợ màn hình Retina sắc nét (xử lý `devicePixelRatio`).
  - Cảnh báo nhấp nháy đỏ **"PHÁT HIỆN TAI NẠN"** khi thời gian video nằm trong khoảng xảy ra sự cố.
  - Công tắc bật/tắt hiển thị khung nhận diện tai nạn và khung phương tiện xe.
  - Thanh timeline dưới video đánh dấu màu đỏ các khoảng xảy ra tai nạn, click để tua trực tiếp.
- **3 Trang Giao Diện Hoàn Chỉnh (Tông màu Navy Blue + Trắng, Cảnh báo Đỏ):**
  1. **Trang 1 (Phân tích video):** Vùng kéo thả file, xem trước video, đo thời lượng/dung lượng, thanh tiến độ % (polling mỗi 1 giây) và tự động chuyển trang khi xong.
  2. **Trang 2 (Kết quả phân tích):** Banner kết luận lớn ("Phát hiện N vụ tai nạn" hoặc "An toàn"), video player tích hợp canvas bounding box, bảng bằng chứng các sự kiện tai nạn (ảnh chứng cứ, timestamp, confidence, xe liên quan, click để tua).
  3. **Trang 3 (Lịch sử phân tích):** Bảng quản lý video đã phân tích, tìm kiếm theo tên, xem lại kết quả hoặc xóa video (có hộp thoại xác nhận).

---

## 🛠️ 2. Công Nghệ Sử Dụng

| Thành phần | Công nghệ / Thư viện |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, React Router v6, Axios, Lucide Icons |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, OpenCV, PyTorch, Ultralytics YOLO, Hugging Face Hub, ImageIO-FFmpeg |
| **Database** | MySQL 8.0 (kết hợp SQLAlchemy 2.0 + PyMySQL với bảng mã `utf8mb4` hỗ trợ tiếng Việt có dấu, connection pool `pool_pre_ping=True`) |
| **Xử lý nền** | FastAPI BackgroundTasks / Threading, polling HTTP mỗi 1 giây |

---

## 📂 3. Cấu Trúc Thư Mục

```text
traffic-accident-detection/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, static evidence, SPA fallback
│   │   ├── config.py          # Tập trung toàn bộ tham số cấu hình hệ thống
│   │   ├── database.py        # SQLAlchemy models (Video, Event) + kết nối MySQL
│   │   ├── routes.py          # API upload, status, list, detail, result, stream, delete
│   │   └── services/
│   │       ├── pipeline.py    # AI Pipeline (YOLO11x + YOLO11n ByteTrack)
│   │       ├── temporal.py    # Xử lý chuỗi thời gian, gộp sự kiện, xuất ảnh bằng chứng
│   │       └── video_utils.py # FFmpeg transcode H.264, đọc metadata
│   ├── scripts/
│   │   ├── run_pipeline.py    # Script CLI chạy kiểm tra độ chính xác & tính Precision/Recall/F1
│   │   └── init_db.sql        # Script SQL tạo cơ sở dữ liệu MySQL
│   ├── weights/               # Chứa epoch61.pt và yolo11n.pt
│   ├── storage/
│   │   ├── videos/            # Lưu trữ video gốc / transcoded
│   │   ├── evidence/          # Lưu trữ ảnh bằng chứng sự kiện tai nạn
│   │   └── results/           # Lưu trữ file JSON kết quả chi tiết từng frame
│   ├── tests/                 # Unit tests & API test suite
│   ├── .env.example           # File mẫu cấu hình biến môi trường
│   ├── .env                   # File cấu hình chính thức
│   └── requirements.txt       # Danh sách thư viện Python cần thiết
├── frontend/
│   ├── src/
│   │   ├── components/        # Sidebar, Navbar, CanvasOverlay
│   │   ├── pages/             # UploadPage, ResultPage, HistoryPage
│   │   ├── api.js             # Axios API client
│   │   ├── App.jsx            # Định tuyến React Router
│   │   └── main.jsx           # Khởi tạo React
│   ├── package.json           # Danh sách thư viện npm
│   ├── tailwind.config.js     # Cấu hình Tailwind CSS (tông màu Navy)
│   └── vite.config.js         # Cấu hình Vite & API Proxy
└── README.md                  # Hướng dẫn chi tiết
```

---

## 🚀 4. Hướng Dẫn Cài Đặt & Chạy Hệ Thống Từng Bước

### Bước 1: Yêu cầu môi trường
Đảm bảo máy tính đã cài đặt:
- **Python**: Phiên bản 3.10 hoặc 3.11 ([Tải Python](https://www.python.org/downloads/))
- **Node.js**: Phiên bản 18 trở lên ([Tải Node.js](https://nodejs.org/))
- **MySQL Server**: Phiên bản 8.0 ([Tải MySQL](https://dev.mysql.com/downloads/installer/)) hoặc XAMPP / MariaDB.
- **FFmpeg**: Đã được tự động tích hợp thông qua gói `imageio-ffmpeg` trong Python (hoặc có thể cài thêm FFmpeg vào PATH hệ thống).

---

### Bước 2: Khởi tạo Cơ Sở Dữ Liệu MySQL
1. Khởi động dịch vụ MySQL trên máy tính (qua Services hoặc XAMPP Control Panel).
2. Mở MySQL Workbench hoặc terminal dòng lệnh MySQL và thực thi file `backend/scripts/init_db.sql`:
```powershell
# Trên Windows PowerShell:
Get-Content backend/scripts/init_db.sql | mysql -u root -p

# Hoặc trên Command Prompt (cmd) / Linux:
# mysql -u root -p < backend/scripts/init_db.sql
```
*Lưu ý: Nếu chưa bật MySQL, hệ thống có cơ chế tự động báo lỗi tiếng Việt thân thiện và tạm kích hoạt chế độ Fallback SQLite local để phục vụ chạy thử nghiệm mà không bị crash.*

---

### Bước 3: Cấu hình biến môi trường Backend
Tạo file `backend/.env` từ file `backend/.env.example`:
```bash
cp backend/.env.example backend/.env
```
Mở file `backend/.env` và cập nhật thông tin tài khoản MySQL của bạn:
```env
# Cấu hình kết nối MySQL (dùng utf8mb4 để hỗ trợ tên tiếng Việt có dấu)
DATABASE_URL=mysql+pymysql://root:mat_khau_cua_ban@localhost:3306/traffic_accident?charset=utf8mb4

# Cấu hình Server
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Tham số AI Pipeline
ACCIDENT_CONF_THRESHOLD=0.5
MIN_CONSECUTIVE_DETECTIONS=3
EVENT_MERGE_GAP_SECONDS=3.0
INFER_STRIDE=3
MAX_UPLOAD_SIZE_MB=500
DEVICE=auto
```

---

### Bước 4: Cài đặt thư viện Backend (Python)
Mở terminal tại thư mục gốc của dự án:
```bash
# Tạo môi trường ảo Python
python -m venv venv

# Kích hoạt môi trường ảo:
# Trên Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Hoặc trên Linux/macOS:
# source venv/bin/activate

# Nâng cấp pip và cài đặt thư viện
pip install -r backend/requirements.txt
```

---

### Bước 5: Tải trọng số mô hình AI (Weights)
Hệ thống có cơ chế tự động tải trọng số từ Hugging Face khi khởi động server lần đầu. Bạn cũng có thể tải trước bằng dòng lệnh:
```bash
python -c "import sys; sys.path.append('backend'); from app.services.pipeline import download_weights_if_missing; download_weights_if_missing()"
```
Sau bước này, trong thư mục `backend/weights/` sẽ có 2 file:
- `epoch61.pt` (~110MB - mô hình YOLO11x phát hiện tai nạn)
- `yolo11n.pt` (~5MB - mô hình theo dõi phương tiện COCO)

---

### Bước 6: Cài đặt và khởi chạy Frontend (React + Vite)
Mở một terminal mới:
```bash
cd frontend

# Cài đặt các gói npm
npm install

# Khởi chạy máy chủ phát triển (Development Server)
npm run dev
```
Giao diện người dùng sẽ chạy tại địa chỉ: **`http://localhost:5173`** (đã được cấu hình tự động proxy các request `/api` và `/evidence` sang Backend port 8000).

---

### Bước 7: Khởi chạy Backend (FastAPI)
Mở terminal thứ hai (với môi trường ảo đã kích hoạt):
```bash
# Thiết lập đường dẫn PYTHONPATH cho backend
# Trên PowerShell Windows:
$env:PYTHONPATH="backend"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Hoặc trên Command Prompt (cmd):
# set PYTHONPATH=backend
# python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation (Swagger UI) có sẵn tại: **`http://localhost:8000/docs`**

---

## 🧪 5. Script Kiểm Tra Độ Chính Xác AI Pipeline (`run_pipeline.py`)

File `backend/scripts/run_pipeline.py` cho phép bạn chạy kiểm thử độc lập pipeline AI từ dòng lệnh trên một video hoặc toàn bộ thư mục video mà không cần mở trình duyệt web.

### 1. Chạy trên một video đơn lẻ:
```bash
.\venv\Scripts\python.exe backend/scripts/run_pipeline.py duong_dan/toi/video.mp4
```
Kết quả in ra chi tiết:
- Thông số kỹ thuật video (FPS, độ phân giải, thời lượng).
- Kết luận có tai nạn hay không, số sự kiện phát hiện.
- Chi tiết từng sự kiện: timestamp bắt đầu, kết thúc, thời điểm đỉnh (`peak_time`), độ tin cậy cực đại (`max_confidence`), các `track_id` xe liên quan.
- File JSON kết quả được lưu tại `backend/storage/results/{video_name}.json`.

### 2. Đánh giá độ chính xác (Precision, Recall, F1) với file nhãn:
Chuẩn bị file `labels.csv` dạng:
```csv
filename,có_tai_nạn
video1.mp4,1
video2.mp4,0
video3.mp4,1
```
Chạy lệnh đánh giá:
```bash
.\venv\Scripts\python.exe backend/scripts/run_pipeline.py thu_muc_chua_video/ --labels labels.csv
```
Hệ thống sẽ tự động tổng hợp ma trận nhầm lẫn và bảng chỉ số:
- **True Positives (TP)**, **False Positives (FP)**, **True Negatives (TN)**, **False Negatives (FN)**
- **Accuracy (%)**
- **Precision (%)**
- **Recall (%)**
- **F1-Score (%)**

Giúp bạn dễ dàng tinh chỉnh các ngưỡng `conf` và `stride` trong `backend/.env` để đưa số liệu báo cáo vào đồ án/bài tập lớn.

---

## 💡 6. Các Điểm Nổi Bật Về Kỹ Thuật

1. **Chuẩn hóa tọa độ Bounding Box:** Toàn bộ tọa độ $[x_1, y_1, x_2, y_2]$ được chuẩn hóa về dải $[0.0, 1.0]$. Frontend tự động scale theo khung hình hiển thị thực tế của video, đảm bảo box bám chính xác 100% ở mọi kích thước màn hình và chế độ toàn màn hình.
2. **Khắc phục triệt để hiện tượng trễ & rung giật box:**
   - Không dùng `setInterval` (dễ lệch frame khi video giật lag).
   - Tận dụng `video.requestVideoFrameCallback` để đồng bộ đúng chu kỳ vẽ của từng frame video từ GPU.
   - Nội suy tuyến tính vị trí giữa hai frame kết quả liền kề kết hợp thuật toán làm mượt EMA (Exponential Moving Average).
3. **Bảo toàn chất lượng video gốc:** Video không bị nén lại hay bị vẽ cứng box lên các pixel gốc, giúp video luôn sắc nét tối đa.
4. **Tiêu chuẩn HTTP Range Streaming (RFC 7233):** Backend hỗ trợ trả về mã `206 Partial Content`, cho phép người dùng tua nhanh đến bất kỳ thời điểm nào trên video một cách tức thì.

---

## 👥 7. Tác Quyền & Đồ Án
Dự án được xây dựng phục vụ cho Bài tập lớn môn Học máy / Thị giác máy tính / Đồ án chuyên ngành Công nghệ Thông tin. Mọi đóng góp và phản hồi xin vui lòng tạo Issue hoặc Pull Request trên kho lưu trữ.
