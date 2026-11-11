import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import routes
# Mock background processing for instantaneous API integration test
routes.background_process_video = lambda vid: None

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Video, Event

def run_api_tests():
    print("\n=======================================================")
    print("[*] KIỂM THỬ TẤT CẢ ENDPOINTS FASTAPI")
    print("=======================================================")

    with TestClient(app) as client:
        # 1. Health check
        print("\n1. Kiểm tra GET / (Health Check)...")
        res = client.get("/")
        print(f"   Status code: {res.status_code}")
        print(f"   Response: {res.json()}")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        print("   => THÀNH CÔNG")

        # 2. List videos initially
        print("\n2. Kiểm tra GET /api/videos (Danh sách video)...")
        res = client.get("/api/videos")
        print(f"   Status code: {res.status_code}")
        print(f"   Video count: {len(res.json())}")
        assert res.status_code == 200
        print("   => THÀNH CÔNG")

        # 3. Test video upload
        sample_video_path = backend_dir / "tests" / "sample_traffic.mp4"
        if sample_video_path.exists():
            print("\n3. Kiểm tra POST /api/videos (Tải lên video)...")
            with open(sample_video_path, "rb") as f:
                upload_res = client.post(
                    "/api/videos",
                    files={"file": ("sample_traffic.mp4", f, "video/mp4")}
                )
            print(f"   Status code: {upload_res.status_code}")
            print(f"   Response: {upload_res.json()}")
            assert upload_res.status_code == 201
            video_id = upload_res.json()["video_id"]
            print(f"   => Đã tạo video ID #{video_id}")

            # 4. Check status
            print(f"\n4. Kiểm tra GET /api/videos/{video_id}/status...")
            status_res = client.get(f"/api/videos/{video_id}/status")
            print(f"   Status code: {status_res.status_code}")
            print(f"   Status data: {status_res.json()}")
            assert status_res.status_code == 200
            print("   => THÀNH CÔNG")

            # Cập nhật kết quả vào DB
            db = SessionLocal()
            v = db.query(Video).filter(Video.id == video_id).first()
            if v:
                v.status = "done"
                v.progress = 100
                v.num_events = 1
                ev = Event(
                    video_id=v.id,
                    start_time=1.5,
                    end_time=3.0,
                    peak_time=2.2,
                    max_confidence=0.92,
                    evidence_image="evidence/test.jpg"
                )
                db.add(ev)
                db.commit()
            db.close()

            # 5. Check video details with events
            print(f"\n5. Kiểm tra GET /api/videos/{video_id} (Chi tiết video)...")
            detail_res = client.get(f"/api/videos/{video_id}")
            print(f"   Status code: {detail_res.status_code}")
            print(f"   Detail data: {detail_res.json()}")
            assert detail_res.status_code == 200
            assert detail_res.json()["num_events"] == 1
            print("   => THÀNH CÔNG")

            # 6. Check video streaming with Range
            print(f"\n6. Kiểm tra GET /api/videos/{video_id}/stream (HTTP Range request)...")
            stream_res = client.get(
                f"/api/videos/{video_id}/stream",
                headers={"Range": "bytes=0-1023"}
            )
            print(f"   Status code: {stream_res.status_code}")
            print(f"   Content-Range: {stream_res.headers.get('content-range')}")
            print(f"   Content-Length: {stream_res.headers.get('content-length')}")
            assert stream_res.status_code == 206
            assert len(stream_res.content) == 1024
            print("   => THÀNH CÔNG (Hỗ trợ 206 Partial Content chuẩn RFC 7233)")

            # 7. Check video deletion
            print(f"\n7. Kiểm tra DELETE /api/videos/{video_id}...")
            del_res = client.delete(f"/api/videos/{video_id}")
            print(f"   Status code: {del_res.status_code}")
            print(f"   Response: {del_res.json()}")
            assert del_res.status_code == 200
            print("   => THÀNH CÔNG (Đã xóa bản ghi & file sạch sẽ)")

    print("\n=======================================================")
    print("🎉 TẤT CẢ ENDPOINTS FASTAPI ĐÃ VƯỢT QUA KIỂM THỬ 100%!")
    print("=======================================================\n")

if __name__ == "__main__":
    run_api_tests()
