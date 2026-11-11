import os
import sys
import argparse
import csv
from pathlib import Path

# Thêm đường dẫn backend vào sys.path để import được app
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

from app.config import (
    ACCIDENT_CONF_THRESHOLD,
    INFER_STRIDE,
    RESULTS_DIR,
    ALLOWED_EXTENSIONS,
)
from app.services.pipeline import run_video_pipeline

def format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 10)
    return f"{m:02d}:{s:02d}.{ms}"

def process_single_video(
    video_path: Path,
    infer_stride: int,
    conf_threshold: float,
    video_id: str = None
) -> dict:
    if video_id is None:
        video_id = video_path.stem

    print(f"\n=======================================================")
    print(f"[*] Đang xử lý video: {video_path.name}")
    print(f"    Đường dẫn: {video_path}")
    print(f"    Tham số: stride={infer_stride}, conf={conf_threshold}")
    print(f"=======================================================")

    def progress_cb(percent: int, msg: str):
        sys.stdout.write(f"\r    [{percent:3d}%] {msg}")
        sys.stdout.flush()

    res = run_video_pipeline(
        video_path=video_path,
        video_id=video_id,
        progress_callback=progress_cb,
        infer_stride=infer_stride,
        conf_threshold=conf_threshold,
    )
    print("\n")

    summary = res["summary"]
    events = res["events"]
    meta = res["meta"]

    print(f"[-] KẾT QUẢ PHÂN TÍCH:")
    print(f"    - Thời lượng: {meta['duration']}s ({meta['total_frames']} frames @ {meta['fps']} FPS)")
    print(f"    - Có tai nạn: {'CÓ' if summary['has_accident'] else 'KHÔNG'}")
    print(f"    - Số vụ tai nạn phát hiện: {summary['num_events']}")

    if events:
        print(f"    - Danh sách sự kiện:")
        for ev in events:
            print(
                f"      + Sự kiện #{ev['id']}: Từ {format_time(ev['start'])} ({ev['start']}s) "
                f"đến {format_time(ev['end'])} ({ev['end']}s) | "
                f"Peak: {format_time(ev['peak_time'])} (Conf: {int(ev['max_confidence']*100)}%) | "
                f"Xe liên quan IDs: {ev['track_ids']} | "
                f"Ảnh bằng chứng: {ev['evidence_image']}"
            )
    else:
        print("    - Không phát hiện sự cố tai nạn nào.")

    result_json_path = RESULTS_DIR / f"{video_id}.json"
    print(f"[-] File JSON kết quả: {result_json_path}")
    return res

def evaluate_metrics(predictions: dict, labels_file: Path):
    """
    Đọc file CSV ground truth và tính toán Precision, Recall, F1-score ở cấp độ video.
    """
    if not labels_file.exists():
        print(f"[!] File nhãn không tồn tại: {labels_file}")
        return

    ground_truth = {}
    with open(labels_file, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                fname = row[0].strip()
                try:
                    label = int(row[1].strip())
                    ground_truth[fname] = label
                    # Lưu thêm stem để dễ đối chiếu
                    ground_truth[Path(fname).stem] = label
                except ValueError:
                    continue

    tp, fp, tn, fn = 0, 0, 0, 0
    print("\n" + "=" * 65)
    print(" BẢNG ĐỐI CHIẾU NHÃN THỰC TẾ (GROUND TRUTH) & KẾT QUẢ DỰ ĐOÁN")
    print("=" * 65)
    print(f"{'Tên file':<30} | {'Thực tế':<10} | {'Dự đoán':<10} | {'Kết quả':<8}")
    print("-" * 65)

    for vname, pred_has_accident in predictions.items():
        vstem = Path(vname).stem
        actual = ground_truth.get(vname, ground_truth.get(vstem))
        if actual is None:
            continue

        pred = 1 if pred_has_accident else 0
        if actual == 1 and pred == 1:
            tp += 1
            res_str = "TP (Đúng)"
        elif actual == 0 and pred == 1:
            fp += 1
            res_str = "FP (Báo sai)"
        elif actual == 0 and pred == 0:
            tn += 1
            res_str = "TN (Đúng)"
        else: # actual == 1 and pred == 0
            fn += 1
            res_str = "FN (Bỏ sót)"

        print(f"{vname:<30} | {actual:<10} | {pred:<10} | {res_str:<8}")

    total = tp + fp + tn + fn
    if total == 0:
        print("[!] Không có video nào khớp với danh sách trong file nhãn.")
        return

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("=" * 65)
    print(" ĐÁNH GIÁ ĐỘ CHÍNH XÁC MÔ HÌNH (ACCURACY EVALUATION METRICS)")
    print("=" * 65)
    print(f" Tổng số video kiểm thử: {total}")
    print(f" True Positives  (TP) : {tp}")
    print(f" False Positives (FP) : {fp}")
    print(f" True Negatives  (TN) : {tn}")
    print(f" False Negatives (FN) : {fn}")
    print("-" * 65)
    print(f" Accuracy             : {accuracy * 100:.2f}%")
    print(f" Precision            : {precision * 100:.2f}%")
    print(f" Recall               : {recall * 100:.2f}%")
    print(f" F1-Score             : {f1 * 100:.2f}%")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(
        description="Script kiểm tra độ chính xác AI Pipeline phát hiện tai nạn giao thông."
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Đường dẫn tới file video đơn lẻ hoặc thư mục chứa các video."
    )
    parser.add_argument(
        "--stride",
        type=int,
        default=INFER_STRIDE,
        help=f"Khoảng cách bước nhảy frame khi chạy YOLO11x (mặc định: {INFER_STRIDE})."
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=ACCIDENT_CONF_THRESHOLD,
        help=f"Ngưỡng confidence phát hiện tai nạn (mặc định: {ACCIDENT_CONF_THRESHOLD})."
    )
    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="Đường dẫn file CSV nhãn (cột: filename, có_tai_nạn 0/1) để tính Precision/Recall/F1."
    )

    args = parser.parse_args()
    input_path = Path(args.input_path)

    if not input_path.exists():
        print(f"[LỖI] Đường dẫn không tồn tại: {input_path}")
        sys.exit(1)

    video_files = []
    if input_path.is_file():
        video_files.append(input_path)
    elif input_path.is_dir():
        for p in input_path.iterdir():
            if p.suffix.lower() in ALLOWED_EXTENSIONS:
                video_files.append(p)
        video_files.sort()

    if not video_files:
        print(f"[!] Không tìm thấy file video hợp lệ ({', '.join(ALLOWED_EXTENSIONS)}) tại: {input_path}")
        sys.exit(1)

    predictions = {}
    for vid in video_files:
        try:
            res = process_single_video(
                video_path=vid,
                infer_stride=args.stride,
                conf_threshold=args.conf,
            )
            predictions[vid.name] = res["summary"]["has_accident"]
        except Exception as e:
            print(f"[!] Lỗi khi xử lý video {vid.name}: {e}")

    if args.labels:
        evaluate_metrics(predictions, Path(args.labels))

if __name__ == "__main__":
    main()
