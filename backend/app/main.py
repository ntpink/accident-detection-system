import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import (
    EVIDENCE_DIR,
    STORAGE_DIR,
    BASE_DIR,
    HOST,
    PORT,
    DEBUG,
)
from app.database import init_db
from app.services.pipeline import get_model_manager
from app.routes import router as video_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Sự kiện vòng đời ứng dụng:
    - Khởi tạo Database schema
    - Tải trước trọng số AI vào RAM khi khởi động để sẵn sàng xử lý ngay
    """
    print("=============================================================")
    print("🚀 [Khởi động] Hệ thống Phát hiện Tai nạn Giao thông (Backend)")
    print("=============================================================")
    init_db()
    
    # Nạp trước model AI một lần duy nhất
    print("[Hệ thống] Đang khởi động mô hình AI...")
    get_model_manager()
    print("[Hệ thống] Mô hình AI đã sẵn sàng phục vụ yêu cầu!")
    print("=============================================================")
    yield
    print("[Hệ thống] Tắt dịch vụ backend thành công.")

app = FastAPI(
    title="Traffic Accident Detection API",
    description="Hệ thống phân tích và phát hiện sự cố tai nạn giao thông từ video",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS để Frontend React gọi API mượt mà
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cung cấp static file cho các ảnh bằng chứng (evidence)
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")

# Đăng ký các route API
app.include_router(video_router)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Traffic Accident Detection API",
        "version": "1.0.0",
    }

# Phục vụ Frontend React (Single Page Application) nếu đã build thư mục frontend/dist
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_spa(full_path: str):
        # Không can thiệp vào các đường dẫn API hoặc static evidence
        if full_path.startswith("api/") or full_path.startswith("evidence/"):
            return None
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=DEBUG)
