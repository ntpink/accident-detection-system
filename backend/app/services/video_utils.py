import os
import shutil
import subprocess
import cv2
from pathlib import Path
from typing import Dict, Any, Tuple

def get_ffmpeg_executable() -> str:
    """
    Tìm đường dẫn ffmpeg: ưu tiên hệ thống (PATH), nếu không có thì dùng imageio_ffmpeg.
    """
    cmd = shutil.which("ffmpeg")
    if cmd:
        return cmd
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    
    # Kiểm tra một số đường dẫn phổ biến trên Windows
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
            
    raise RuntimeError(
        "Không tìm thấy công cụ ffmpeg trên hệ thống! "
        "Vui lòng cài đặt ffmpeg và thêm vào PATH hoặc chạy 'pip install imageio-ffmpeg'."
    )

def get_video_metadata(video_path: str | Path) -> Dict[str, Any]:
    """
    Đọc thông số kỹ thuật của video bằng OpenCV: fps, width, height, total_frames, duration.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Không thể mở file video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Nếu không đọc được số frame chính xác
    if total_frames <= 0:
        total_frames = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    
    duration = (total_frames / fps) if fps > 0 and total_frames > 0 else 0.0
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
    
    cap.release()
    
    return {
        "fps": round(fps, 2),
        "width": width,
        "height": height,
        "total_frames": total_frames,
        "duration": round(duration, 2),
        "fourcc": fourcc
    }

def is_h264_mp4(video_path: str | Path) -> bool:
    """
    Kiểm tra nhanh xem video có phải định dạng MP4 và dùng codec H.264/AVC1 hay không.
    """
    path = Path(video_path)
    if path.suffix.lower() != ".mp4":
        return False
        
    try:
        ffmpeg_bin = get_ffmpeg_executable()
        # Chạy ffmpeg -i để kiểm tra thông tin stream video
        res = subprocess.run(
            [ffmpeg_bin, "-i", str(video_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        stderr = res.stderr.lower()
        if "video: h264" in stderr or "video: avc1" in stderr:
            return True
    except Exception:
        pass
        
    return False

def transcode_to_h264(input_path: str | Path, output_path: str | Path) -> str:
    """
    Chuyển đổi video sang chuẩn H.264 (MP4) với chất lượng cao (crf 18, yuv420p, +faststart)
    để trình duyệt HTML5 (Chrome, Edge, Firefox, Safari) có thể phát mượt mà qua HTTP Range.
    """
    ffmpeg_bin = get_ffmpeg_executable()
    input_str = str(input_path)
    output_str = str(output_path)
    
    # Lệnh ffmpeg theo yêu cầu
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_str,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "128k",
        output_str
    ]
    
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return output_str
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Lỗi khi chuyển đổi định dạng video bằng ffmpeg: {e.stderr}"
        ) from e
