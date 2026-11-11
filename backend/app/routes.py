import os
import shutil
import json
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    BackgroundTasks,
    Request,
    status,
)
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import (
    MAX_UPLOAD_SIZE_MB,
    ALLOWED_EXTENSIONS,
    VIDEOS_DIR,
    EVIDENCE_DIR,
    RESULTS_DIR,
    INFER_STRIDE,
    ACCIDENT_CONF_THRESHOLD,
)
from app.database import get_db, SessionLocal, Video, Event
from app.services.video_utils import (
    get_video_metadata,
    is_h264_mp4,
    transcode_to_h264,
)
from app.services.pipeline import run_video_pipeline

router = APIRouter(prefix="/api/videos", tags=["Videos"])

def background_process_video(video_id: int):
    """
    Hàm xử lý video nền: chạy pipeline AI, cập nhật tiến độ vào DB,
    và lưu thông tin sự kiện sau khi hoàn tất.
    """
    db: Session = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return

        video.status = "processing"
        video.progress = 1
        db.commit()

        def update_progress(percent: int, message: str):
            try:
                # Tạo session mới hoặc dùng session hiện tại để cập nhật tiến độ
                v = db.query(Video).filter(Video.id == video_id).first()
                if v:
                    v.progress = percent
                    v.error_message = message
                    db.commit()
            except Exception as pe:
                print(f"[Tiến độ lỗi]: {pe}")

        # Chạy pipeline AI
        result = run_video_pipeline(
            video_path=video.stored_path,
            video_id=video.id,
            progress_callback=update_progress,
            infer_stride=INFER_STRIDE,
            conf_threshold=ACCIDENT_CONF_THRESHOLD,
        )

        events_data = result.get("events", [])

        # Thêm các sự kiện vào database
        for ev in events_data:
            db_event = Event(
                video_id=video.id,
                start_time=ev["start"],
                end_time=ev["end"],
                peak_time=ev["peak_time"],
                max_confidence=ev["max_confidence"],
                evidence_image=ev["evidence_image"],
            )
            db.add(db_event)

        video.status = "done"
        video.progress = 100
        video.num_events = len(events_data)
        video.error_message = None
        db.commit()

    except Exception as e:
        print(f"[Lỗi xử lý video {video_id}]: {e}")
        try:
            v = db.query(Video).filter(Video.id == video_id).first()
            if v:
                v.status = "error"
                v.error_message = f"Lỗi xử lý: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Tải lên video mới, kiểm tra dung lượng/định dạng, transcode sang H.264 nếu cần,
    và bắt đầu tác vụ phân tích nền.
    """
    filename = file.filename
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file '{ext}' không được hỗ trợ. Vui lòng tải lên file: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Đọc và lưu tạm file
    temp_dir = VIDEOS_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_upload_path = temp_dir / f"upload_{int(datetime.utcnow().timestamp())}_{filename}"

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_size = 0

    try:
        with open(temp_upload_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024) # 1MB chunk
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_bytes:
                    buffer.close()
                    temp_upload_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Dung lượng video ({round(total_size / (1024*1024), 1)}MB) vượt quá giới hạn cho phép ({MAX_UPLOAD_SIZE_MB}MB)!",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        temp_upload_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lưu file tải lên: {str(e)}",
        )

    # Tạo bản ghi trong Database trước để lấy video_id
    video_record = Video(
        filename=filename,
        stored_path="",
        duration=0.0,
        status="queued",
        progress=0,
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    # Đích lưu trữ chính thức
    final_filename = f"{video_record.id}_{Path(filename).stem}.mp4"
    final_path = VIDEOS_DIR / final_filename

    # Kiểm tra codec video: nếu không phải H.264 MP4 thì chuyển mã bằng ffmpeg
    try:
        if is_h264_mp4(temp_upload_path):
            shutil.move(str(temp_upload_path), str(final_path))
        else:
            transcode_to_h264(temp_upload_path, final_path)
            temp_upload_path.unlink(missing_ok=True)
    except Exception as e:
        # Nếu chuyển mã lỗi, thử di chuyển file gốc nếu có thể
        if temp_upload_path.exists():
            shutil.move(str(temp_upload_path), str(final_path))

    # Đọc metadata thời lượng video
    try:
        meta = get_video_metadata(final_path)
        video_record.duration = meta["duration"]
    except Exception:
        video_record.duration = 0.0

    video_record.stored_path = str(final_path)
    db.commit()

    # Khởi động tác vụ nền phân tích AI
    background_tasks.add_task(background_process_video, video_record.id)

    return {"video_id": video_record.id, "filename": filename, "duration": video_record.duration}

@router.get("")
def list_videos(db: Session = Depends(get_db)):
    """
    Lấy danh sách tất cả các video đã phân tích (Lịch sử).
    """
    videos = db.query(Video).order_by(desc(Video.created_at)).all()
    return [
        {
            "id": v.id,
            "filename": v.filename,
            "duration": v.duration,
            "status": v.status,
            "progress": v.progress,
            "num_events": v.num_events,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else "",
        }
        for v in videos
    ]

@router.get("/{video_id}/status")
def get_video_status(video_id: int, db: Session = Depends(get_db)):
    """
    Lấy trạng thái và tiến độ xử lý của video để polling.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy video với ID: {video_id}",
        )
    return {
        "status": video.status,
        "progress": video.progress,
        "message": video.error_message or "",
    }

@router.get("/{video_id}")
def get_video_details(video_id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin chi tiết của một video kèm danh sách các vụ tai nạn phát hiện được.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy video với ID: {video_id}",
        )

    events = [
        {
            "id": e.id,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "peak_time": e.peak_time,
            "max_confidence": e.max_confidence,
            "evidence_image": e.evidence_image,
        }
        for e in video.events
    ]

    return {
        "id": video.id,
        "filename": video.filename,
        "duration": video.duration,
        "status": video.status,
        "progress": video.progress,
        "error_message": video.error_message,
        "num_events": video.num_events,
        "created_at": video.created_at.strftime("%Y-%m-%d %H:%M:%S") if video.created_at else "",
        "events": events,
    }

@router.get("/{video_id}/result")
def get_video_result(video_id: int):
    """
    Trả về file JSON chứa kết quả phân tích AI chi tiết theo từng frame.
    """
    result_path = RESULTS_DIR / f"{video_id}.json"
    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có kết quả JSON cho video ID: {video_id}",
        )
    try:
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đọc file kết quả JSON: {str(e)}",
        )

@router.get("/{video_id}/stream")
def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Phát video với hỗ trợ HTTP Range requests (RFC 7233) để trình duyệt
    có thể tua (seek) đến bất kỳ mốc thời gian nào.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not os.path.isfile(video.stored_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File video không tồn tại trên hệ thống lưu trữ.",
        )

    file_path = video.stored_path
    file_size = os.path.getsize(file_path)

    range_header = request.headers.get("range")
    start = 0
    end = file_size - 1

    if range_header:
        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        if parts[0]:
            start = int(parts[0])
        if len(parts) > 1 and parts[1]:
            end = int(parts[1])

    # Giới hạn kích thước chunk tối đa mỗi lần đọc
    chunk_size = 1024 * 1024 # 1MB
    content_length = (end - start) + 1

    def iter_file(start_pos: int, bytes_to_read: int):
        with open(file_path, "rb") as f:
            f.seek(start_pos)
            remaining = bytes_to_read
            while remaining > 0:
                current_chunk = min(chunk_size, remaining)
                data = f.read(current_chunk)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
    }

    status_code = status.HTTP_206_PARTIAL_CONTENT if range_header else status.HTTP_200_OK
    return StreamingResponse(
        iter_file(start, content_length),
        status_code=status_code,
        headers=headers,
    )

@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    """
    Xóa video, các ảnh bằng chứng liên quan, file kết quả JSON và bản ghi DB.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy video với ID: {video_id}",
        )

    # 1. Xóa file video gốc/transcoded
    if video.stored_path and os.path.isfile(video.stored_path):
        try:
            os.remove(video.stored_path)
        except Exception as e:
            print(f"[Xóa file video lỗi]: {e}")

    # 2. Xóa các ảnh bằng chứng (evidence)
    for ev in video.events:
        ev_file = EVIDENCE_DIR / Path(ev.evidence_image).name
        if ev_file.exists():
            try:
                ev_file.unlink()
            except Exception as e:
                print(f"[Xóa ảnh bằng chứng lỗi]: {e}")

    # 3. Xóa file JSON kết quả
    result_path = RESULTS_DIR / f"{video_id}.json"
    if result_path.exists():
        try:
            result_path.unlink()
        except Exception as e:
            print(f"[Xóa JSON kết quả lỗi]: {e}")

    # 4. Xóa bản ghi trong database (CASCADE tự xóa events)
    db.delete(video)
    db.commit()

    return {"success": True, "message": f"Đã xóa thành công video #{video_id}"}
