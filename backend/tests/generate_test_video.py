import cv2
import numpy as np
from pathlib import Path

def create_sample_video(output_path: str, duration_sec: int = 4, fps: int = 30):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration_sec * fps
    for i in range(total_frames):
        # Tạo khung hình mặt đường xám
        frame = np.full((height, width, 3), (70, 70, 70), dtype=np.uint8)
        
        # Vẽ vạch kẻ đường vàng
        cv2.line(frame, (0, height // 2), (width, height // 2), (0, 215, 255), 2)
        
        # Vẽ 2 khối mô phỏng ô tô đang di chuyển
        car1_x = int(50 + (i / total_frames) * 350)
        car1_y = 150
        cv2.rectangle(frame, (car1_x, car1_y), (car1_x + 80, car1_y + 40), (200, 50, 50), -1)
        
        car2_x = int(500 - (i / total_frames) * 200)
        car2_y = 280
        cv2.rectangle(frame, (car2_x, car2_y), (car2_x + 80, car2_y + 40), (50, 150, 200), -1)
        
        # Thêm timestamp text
        cv2.putText(frame, f"Frame {i}/{total_frames}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        out.write(frame)
        
    out.release()
    print(f"Đã tạo video mẫu: {output_path} ({total_frames} frames, {duration_sec}s)")

if __name__ == "__main__":
    create_sample_video("backend/tests/sample_traffic.mp4")
