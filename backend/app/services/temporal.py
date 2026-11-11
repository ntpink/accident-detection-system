import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.config import (
    ACCIDENT_CONF_THRESHOLD,
    MIN_CONSECUTIVE_DETECTIONS,
    EVENT_MERGE_GAP_SECONDS,
    EVIDENCE_DIR,
)

def compute_iou(boxA: List[float], boxB: List[float]) -> float:
    """
    Tính Intersection over Union (IoU) giữa 2 bounding box [x1, y1, x2, y2].
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_width = max(0.0, xB - xA)
    inter_height = max(0.0, yB - yA)
    inter_area = inter_width * inter_height

    if inter_area <= 0:
        return 0.0

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    union_area = boxA_area + boxB_area - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area

def draw_evidence_overlay(
    frame: np.ndarray,
    accident_box: List[float],
    confidence: float,
    vehicles: List[Dict[str, Any]],
    involved_track_ids: List[int],
) -> np.ndarray:
    """
    Vẽ bounding box và nhãn chất lượng cao lên frame gốc tại thời điểm peak để lưu làm ảnh bằng chứng.
    """
    vis_frame = frame.copy()
    h, w = vis_frame.shape[:2]

    # Vẽ các xe liên quan (viền xanh ngọc / cyan)
    for v in vehicles:
        track_id = v.get("id")
        if track_id in involved_track_ids:
            box = v["box"]
            x1, y1, x2, y2 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
            label = f"{v.get('cls', 'car')} #{track_id}"
            
            # Nền chữ cho xe
            (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(vis_frame, (x1, max(0, y1 - th - baseline - 4)), (x1 + tw + 6, max(0, y1)), (255, 200, 0), -1)
            cv2.putText(vis_frame, label, (x1 + 3, max(0, y1 - baseline - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    # Vẽ vùng tai nạn (viền đỏ nổi bật, độ dày 3)
    ax1 = int(accident_box[0] * w)
    ay1 = int(accident_box[1] * h)
    ax2 = int(accident_box[2] * w)
    ay2 = int(accident_box[3] * h)
    cv2.rectangle(vis_frame, (ax1, ay1), (ax2, ay2), (0, 0, 255), 3)

    acc_label = f"ACCIDENT {int(confidence * 100)}%"
    (atw, ath), abaseline = cv2.getTextSize(acc_label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    label_y = max(ath + 6, ay1)
    cv2.rectangle(vis_frame, (ax1, label_y - ath - abaseline - 6), (ax1 + atw + 8, label_y + 2), (0, 0, 255), -1)
    cv2.putText(vis_frame, acc_label, (ax1 + 4, label_y - abaseline), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    return vis_frame

class TemporalProcessor:
    """
    Xử lý chuỗi thời gian các phát hiện:
    - Lọc nhiễu qua MIN_CONSECUTIVE_DETECTIONS
    - Hợp nhất các phát hiện gần nhau (dưới EVENT_MERGE_GAP_SECONDS) thành 1 sự kiện
    - Xác định thời điểm peak, xe liên quan và xuất ảnh bằng chứng JPEG 95
    """

    def __init__(
        self,
        conf_threshold: float = ACCIDENT_CONF_THRESHOLD,
        min_consecutive: int = MIN_CONSECUTIVE_DETECTIONS,
        merge_gap: float = EVENT_MERGE_GAP_SECONDS,
    ):
        self.conf_threshold = conf_threshold
        self.min_consecutive = min_consecutive
        self.merge_gap = merge_gap

        self.current_event: Optional[Dict[str, Any]] = None
        self.consecutive_count: int = 0
        self.confirmed_events: List[Dict[str, Any]] = []

    def process_frame(
        self,
        t: float,
        accidents: List[Dict[str, Any]],
        vehicles: List[Dict[str, Any]],
        raw_frame: Optional[np.ndarray] = None,
    ):
        """
        Nhận kết quả tại mỗi mốc thời gian t (giây).
        """
        # Lọc các phát hiện tai nạn đạt ngưỡng tin cậy
        valid_accidents = [a for a in accidents if a.get("conf", 0.0) >= self.conf_threshold]

        if valid_accidents:
            # Chọn box có confidence cao nhất trên frame này
            best_acc = max(valid_accidents, key=lambda x: x["conf"])
            conf = best_acc["conf"]
            box = best_acc["box"]
            self.consecutive_count += 1

            # Xác định các xe có vùng giao cắt (IoU > 0) với vùng tai nạn
            overlapping_ids = set()
            for v in vehicles:
                vbox = v["box"]
                if compute_iou(box, vbox) > 0.0:
                    overlapping_ids.add(v["id"])

            if self.current_event is None:
                # Bắt đầu ứng viên sự kiện mới
                self.current_event = {
                    "start": t,
                    "end": t,
                    "peak_time": t,
                    "max_confidence": conf,
                    "box": box,
                    "track_ids": list(overlapping_ids),
                    "peak_frame": raw_frame.copy() if raw_frame is not None else None,
                    "peak_vehicles": list(vehicles),
                    "consecutive_hits": 1,
                    "last_seen": t,
                }
            else:
                gap = t - self.current_event["last_seen"]
                if gap <= self.merge_gap:
                    # Gộp vào sự kiện hiện tại
                    self.current_event["end"] = t
                    self.current_event["last_seen"] = t
                    self.current_event["consecutive_hits"] += 1
                    for tid in overlapping_ids:
                        if tid not in self.current_event["track_ids"]:
                            self.current_event["track_ids"].append(tid)

                    # Cập nhật peak nếu độ tin cậy cao hơn
                    if conf > self.current_event["max_confidence"]:
                        self.current_event["max_confidence"] = conf
                        self.current_event["peak_time"] = t
                        self.current_event["box"] = box
                        if raw_frame is not None:
                            self.current_event["peak_frame"] = raw_frame.copy()
                        self.current_event["peak_vehicles"] = list(vehicles)
                else:
                    # Khoảng cách lớn hơn merge_gap -> đóng sự kiện cũ và mở sự kiện mới
                    self._finalize_current_event()
                    self.current_event = {
                        "start": t,
                        "end": t,
                        "peak_time": t,
                        "max_confidence": conf,
                        "box": box,
                        "track_ids": list(overlapping_ids),
                        "peak_frame": raw_frame.copy() if raw_frame is not None else None,
                        "peak_vehicles": list(vehicles),
                        "consecutive_hits": 1,
                        "last_seen": t,
                    }
        else:
            self.consecutive_count = 0
            if self.current_event is not None:
                # Kiểm tra xem khoảng trống đã vượt quá merge_gap chưa
                if (t - self.current_event["last_seen"]) > self.merge_gap:
                    self._finalize_current_event()

    def _finalize_current_event(self):
        """
        Đóng sự kiện hiện tại và lưu vào danh sách nếu đủ số lần phát hiện liên tiếp.
        """
        if self.current_event is not None:
            if self.current_event["consecutive_hits"] >= self.min_consecutive:
                self.confirmed_events.append(self.current_event)
            self.current_event = None

    def finalize(self, video_id: str | int) -> List[Dict[str, Any]]:
        """
        Kết thúc video: đóng các sự kiện còn mở, xuất ảnh bằng chứng và trả về danh sách sự kiện chuẩn.
        """
        self._finalize_current_event()

        final_events = []
        for idx, ev in enumerate(self.confirmed_events, start=1):
            evidence_rel_path = f"evidence/{video_id}_{idx}.jpg"
            evidence_full_path = EVIDENCE_DIR / f"{video_id}_{idx}.jpg"

            # Lưu ảnh bằng chứng ở độ phân giải gốc với chất lượng JPEG 95
            if ev.get("peak_frame") is not None:
                drawn = draw_evidence_overlay(
                    ev["peak_frame"],
                    ev["box"],
                    ev["max_confidence"],
                    ev.get("peak_vehicles", []),
                    ev["track_ids"],
                )
                cv2.imwrite(
                    str(evidence_full_path),
                    drawn,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 95],
                )

            final_events.append({
                "id": idx,
                "start": round(ev["start"], 2),
                "end": round(ev["end"], 2),
                "peak_time": round(ev["peak_time"], 2),
                "max_confidence": round(float(ev["max_confidence"]), 4),
                "box": [round(coord, 4) for coord in ev["box"]],
                "track_ids": sorted(ev["track_ids"]),
                "evidence_image": evidence_rel_path,
            })

        return final_events
