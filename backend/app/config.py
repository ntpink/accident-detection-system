import os
from pathlib import Path
from dotenv import load_dotenv

# Tải cấu hình từ .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STORAGE_DIR = BASE_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"
EVIDENCE_DIR = STORAGE_DIR / "evidence"
RESULTS_DIR = STORAGE_DIR / "results"
WEIGHTS_DIR = BASE_DIR / "weights"

# Đảm bảo các thư mục cần thiết luôn tồn tại
for d in [VIDEOS_DIR, EVIDENCE_DIR, RESULTS_DIR, WEIGHTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/traffic_accident?charset=utf8mb4",
)

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Tham số AI Pipeline & Temporal Processing
ACCIDENT_CONF_THRESHOLD = float(os.getenv("ACCIDENT_CONF_THRESHOLD", "0.5"))
MIN_CONSECUTIVE_DETECTIONS = int(os.getenv("MIN_CONSECUTIVE_DETECTIONS", "3"))
EVENT_MERGE_GAP_SECONDS = float(os.getenv("EVENT_MERGE_GAP_SECONDS", "3.0"))
INFER_STRIDE = int(os.getenv("INFER_STRIDE", "3"))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
DEVICE = os.getenv("DEVICE", "auto")

# Mô hình
HF_REPO_ID = "Enos-123/traffic-accident-detection-yolo11x"
ACCIDENT_MODEL_FILENAME = "epoch61.pt"
ACCIDENT_MODEL_PATH = WEIGHTS_DIR / ACCIDENT_MODEL_FILENAME
VEHICLE_MODEL_FILENAME = "yolo11n.pt"
VEHICLE_MODEL_PATH = WEIGHTS_DIR / VEHICLE_MODEL_FILENAME

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
