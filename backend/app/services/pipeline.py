import os
import time
import json
import torch
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from ultralytics import YOLO
from huggingface_hub import HfApi, hf_hub_download

from app.config import (
    WEIGHTS_DIR,
    ACCIDENT_MODEL_PATH,
    VEHICLE_MODEL_PATH,
    HF_REPO_ID,
    ACCIDENT_MODEL_FILENAME,
    ACCIDENT_CONF_THRESHOLD,
    INFER_STRIDE,
    DEVICE,
    RESULTS_DIR,
)
from app.services.temporal import TemporalProcessor

def download_weights_if_missing():
    """
    Tải file trọng số nếu chưa có trong thư mục weights:
    1. epoch61.pt từ Hugging Face 'Enos-123/traffic-accident-detection-yolo11x'
    2. yolo11n.pt (COCO model từ ultralytics)
    """
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Tải model YOLO11x phát hiện tai nạn
    if not ACCIDENT_MODEL_PATH.exists():
        print(f"[AI Pipeline] Đang tải trọng số tai nạn từ Hugging Face: {HF_REPO_ID}...")
        try:
            api = HfApi()
            repo_files = api.list_repo_files(repo_id=HF_REPO_ID)
            print(f"[AI Pipeline] Danh sách file trong repo HF: {repo_files}")

            target_filename = None
            for candidate in ["weights/epoch61.pt", "epoch61.pt"]:
                if candidate in repo_files:
                    target_filename = candidate
                    break
            
            if target_filename is None:
                # Nếu không tìm thấy tên chính xác epoch61.pt, chọn file .pt có 'epoch61' hoặc .pt đầu tiên
                epoch61_matches = [f for f in repo_files if "epoch61" in f and f.endswith(".pt")]
                if epoch61_matches:
                    target_filename = epoch61_matches[0]
                else:
                    pt_files = [f for f in repo_files if f.endswith(".pt")]
                    if pt_files:
                        target_filename = pt_files[0]
                    else:
                        raise FileNotFoundError(f"Không tìm thấy file .pt nào trong HF repo {HF_REPO_ID}")

            print(f"[AI Pipeline] Tải file trọng số: {target_filename}")
            downloaded_file = hf_hub_download(
                repo_id=HF_REPO_ID,
                filename=target_filename,
                local_dir=str(WEIGHTS_DIR.parent), # Tải vào thư mục backend để giữ nguyên cấu trúc weights/
            )
            # Đảm bảo file nằm đúng tại ACCIDENT_MODEL_PATH (backend/weights/epoch61.pt)
            downloaded_path = Path(downloaded_file)
            if downloaded_path != ACCIDENT_MODEL_PATH and downloaded_path.exists():
                import shutil
                shutil.copyfile(downloaded_path, ACCIDENT_MODEL_PATH)
            print(f"[AI Pipeline] Đã tải thành công trọng số tai nạn: {ACCIDENT_MODEL_PATH}")
        except Exception as e:
            print(f"[AI Pipeline LỖI] Không thể tải model tai nạn từ Hugging Face: {e}")
            raise

    # 2. Tải model YOLO11n nhận diện xe
    if not VEHICLE_MODEL_PATH.exists():
        print(f"[AI Pipeline] Đang tải trọng số xe yolo11n.pt...")
        temp_model = YOLO("yolo11n.pt")
        # Lưu vào thư mục weights nếu ultralytics tải về thư mục làm việc
        if Path("yolo11n.pt").exists() and not VEHICLE_MODEL_PATH.exists():
            import shutil
            shutil.move("yolo11n.pt", str(VEHICLE_MODEL_PATH))
        print(f"[AI Pipeline] Đã chuẩn bị trọng số xe: {VEHICLE_MODEL_PATH}")

class ModelManager:
    """
    Quản lý nạp model duy nhất một lần khi khởi động (Singleton).
    """
    _instance = None

    def __init__(self):
        self.device = self._select_device()
        print(f"[AI Pipeline] Khởi tạo mô hình trên thiết bị: {self.device.upper()}")

        download_weights_if_missing()

        # Nạp model phát hiện tai nạn (YOLO11x)
        print(f"[AI Pipeline] Đang nạp model tai nạn: {ACCIDENT_MODEL_PATH}")
        self.accident_model = YOLO(str(ACCIDENT_MODEL_PATH))
        self.accident_model.to(self.device)

        # In model.names và tìm class 'accident' theo tên động
        print(f"[AI Pipeline] Danh sách lớp của accident_model: {self.accident_model.names}")
        self.accident_class_id = self._find_accident_class_id(self.accident_model.names)
        print(f"[AI Pipeline] Chỉ số lớp tai nạn (accident class id): {self.accident_class_id}")

        # Nạp model nhận diện phương tiện (YOLO11n + ByteTrack)
        print(f"[AI Pipeline] Đang nạp model phương tiện: {VEHICLE_MODEL_PATH}")
        self.vehicle_model = YOLO(str(VEHICLE_MODEL_PATH))
        self.vehicle_model.to(self.device)

        # Lọc các lớp xe trong COCO: car, motorcycle, bus, truck
        self.vehicle_class_ids = self._get_vehicle_class_ids(self.vehicle_model.names)
        print(f"[AI Pipeline] Lớp phương tiện theo dõi: {self.vehicle_class_ids}")

    def _select_device(self) -> str:
        if DEVICE != "auto":
            return DEVICE
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _find_accident_class_id(self, names: Dict[int, str]) -> int:
        for idx, name in names.items():
            name_str = str(name).strip().lower()
            if "accident" in name_str or "crash" in name_str or "collision" in name_str:
                return int(idx)
        # Nếu model chỉ có 1 hoặc 2 lớp mà tên không khớp, kiểm tra lớp 0 hoặc in cảnh báo
        print("[AI Pipeline CẢNH BÁO] Không tìm thấy lớp có tên chứa 'accident', mặc định lấy class 0")
        return 0

    def _get_vehicle_class_ids(self, names: Dict[int, str]) -> List[int]:
        target_names = {"car", "motorcycle", "bus", "truck"}
        ids = []
        for idx, name in names.items():
            if str(name).strip().lower() in target_names:
                ids.append(int(idx))
        return ids

_global_model_manager: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = ModelManager()
    return _global_model_manager

def run_video_pipeline(
    video_path: str | Path,
    video_id: str | int,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    infer_stride: int = INFER_STRIDE,
    conf_threshold: float = ACCIDENT_CONF_THRESHOLD,
) -> Dict[str, Any]:
    """
    Thực thi toàn bộ pipeline AI trên video:
    - YOLO11n + ByteTrack mỗi frame để lấy xe và ID
    - YOLO11x mỗi infer_stride frame để tìm accident
    - Temporal processing để gộp sự kiện, xác nhận và xuất ảnh evidence
    - Lưu kết quả chuẩn vào storage/results/{video_id}.json
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"File video không tồn tại: {video_path}")

    model_mgr = get_model_manager()
    accident_model = model_mgr.accident_model
    vehicle_model = model_mgr.vehicle_model
    accident_class_id = model_mgr.accident_class_id
    vehicle_class_ids = model_mgr.vehicle_class_ids
    device = model_mgr.device

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV không thể mở file video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) or 1
    duration = total_frames / fps

    temporal_proc = TemporalProcessor(conf_threshold=conf_threshold)

    frames_output: List[Dict[str, Any]] = []
    latest_accidents: List[Dict[str, Any]] = []

    last_progress_update_time = time.time()
    frame_idx = 0

    if progress_callback:
        progress_callback(0, "Bắt đầu phân tích video...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            current_time = round(frame_idx / fps, 3)

            # 1. Phát hiện phương tiện và gán Track ID bằng YOLO11n + ByteTrack
            vehicle_results = vehicle_model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=vehicle_class_ids,
                verbose=False,
                device=device,
            )

            vehicles_on_frame: List[Dict[str, Any]] = []
            if vehicle_results and len(vehicle_results) > 0 and vehicle_results[0].boxes is not None:
                boxes = vehicle_results[0].boxes
                for i in range(len(boxes)):
                    box = boxes[i]
                    cls_id = int(box.cls[0].item())
                    cls_name = vehicle_model.names.get(cls_id, "vehicle")
                    # Track id có thể là None nếu frame đầu chưa track được
                    track_id = int(box.id[0].item()) if box.id is not None else (i + 1)
                    
                    xyxy = box.xyxy[0].tolist()
                    # Chuẩn hóa tọa độ về [0, 1]
                    norm_box = [
                        round(max(0.0, min(1.0, xyxy[0] / width)), 4),
                        round(max(0.0, min(1.0, xyxy[1] / height)), 4),
                        round(max(0.0, min(1.0, xyxy[2] / width)), 4),
                        round(max(0.0, min(1.0, xyxy[3] / height)), 4),
                    ]
                    vehicles_on_frame.append({
                        "id": track_id,
                        "cls": cls_name,
                        "box": norm_box
                    })

            # 2. Phát hiện tai nạn bằng YOLO11x mỗi infer_stride frame (mặc định N = 3)
            is_infer_frame = (frame_idx % infer_stride == 0)
            if is_infer_frame:
                accident_results = accident_model.predict(
                    frame,
                    imgsz=640,
                    conf=conf_threshold,
                    device=device,
                    verbose=False,
                )
                current_accidents: List[Dict[str, Any]] = []
                if accident_results and len(accident_results) > 0 and accident_results[0].boxes is not None:
                    aboxes = accident_results[0].boxes
                    for j in range(len(aboxes)):
                        abox = aboxes[j]
                        acls_id = int(abox.cls[0].item())
                        if acls_id == accident_class_id:
                            aconf = float(abox.conf[0].item())
                            axyxy = abox.xyxy[0].tolist()
                            norm_abox = [
                                round(max(0.0, min(1.0, axyxy[0] / width)), 4),
                                round(max(0.0, min(1.0, axyxy[1] / height)), 4),
                                round(max(0.0, min(1.0, axyxy[2] / width)), 4),
                                round(max(0.0, min(1.0, axyxy[3] / height)), 4),
                            ]
                            current_accidents.append({
                                "conf": round(aconf, 4),
                                "box": norm_abox
                            })
                latest_accidents = current_accidents

            # 3. Đưa vào Temporal Processor để phân tích chuỗi thời gian
            # (chỉ truyền raw_frame khi có tai nạn để tiết kiệm bộ nhớ)
            temporal_proc.process_frame(
                t=current_time,
                accidents=latest_accidents,
                vehicles=vehicles_on_frame,
                raw_frame=frame if len(latest_accidents) > 0 else None
            )

            # 4. Ghi nhận thông tin frame cho kết quả JSON
            frames_output.append({
                "t": current_time,
                "vehicles": vehicles_on_frame,
                "accidents": latest_accidents,
            })

            frame_idx += 1

            # 5. Cập nhật tiến độ mỗi 1 giây xử lý
            now = time.time()
            if now - last_progress_update_time >= 1.0 or frame_idx == total_frames:
                percent = min(99, int((frame_idx / total_frames) * 100))
                if progress_callback:
                    progress_callback(percent, f"Đang xử lý: {percent}% ({frame_idx}/{total_frames} khung hình)")
                last_progress_update_time = now

    finally:
        cap.release()

    # 6. Đóng chuỗi temporal processing và xuất danh sách sự kiện
    confirmed_events = temporal_proc.finalize(video_id=video_id)

    # 7. Tạo kết quả JSON chuẩn
    result_data = {
        "meta": {
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "duration": round(duration, 2),
            "total_frames": frame_idx,
            "infer_stride": infer_stride,
        },
        "frames": frames_output,
        "events": confirmed_events,
        "summary": {
            "has_accident": len(confirmed_events) > 0,
            "num_events": len(confirmed_events),
        }
    }

    # Lưu file JSON vào storage/results/{video_id}.json
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"{video_id}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False)

    if progress_callback:
        progress_callback(100, "Hoàn tất phân tích!")

    return result_data
