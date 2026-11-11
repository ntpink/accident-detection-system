-- Khởi tạo database cho hệ thống phát hiện tai nạn giao thông
CREATE DATABASE IF NOT EXISTS traffic_accident 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE traffic_accident;

-- Bảng videos: lưu trữ thông tin video được tải lên và trạng thái xử lý
CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(500) NOT NULL,
    duration FLOAT DEFAULT 0.0,
    status ENUM('queued', 'processing', 'done', 'error') DEFAULT 'queued',
    progress INT DEFAULT 0,
    error_message TEXT DEFAULT NULL,
    num_events INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng events: lưu trữ thông tin các vụ tai nạn phát hiện được trong video
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id INT NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    peak_time FLOAT NOT NULL,
    max_confidence FLOAT NOT NULL,
    evidence_image VARCHAR(500) NOT NULL,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
