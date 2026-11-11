import os
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
load_dotenv(backend_dir / ".env")

def init_mysql_from_python():
    print("=========================================================")
    print(" Khởi tạo Database MySQL qua PyMySQL")
    print("=========================================================")

    # Lấy thông tin kết nối từ biến môi trường hoặc hỏi trực tiếp
    db_url = os.getenv("DATABASE_URL", "")
    
    # Mặc định kết nối tới MySQL localhost
    user = input("Nhập MySQL Username [mặc định: root]: ").strip() or "root"
    password = input("Nhập MySQL Password (để trống nếu không có): ").strip()
    host = "localhost"
    port = 3306

    print(f"\n[*] Đang kết nối tới MySQL Server tại {host}:{port} với user '{user}'...")
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            charset="utf8mb4",
            autocommit=True
        )
    except Exception as e:
        print(f"\n[!] LỖI KẾT NỐI MYSQL: {e}")
        print("    Vui lòng đảm bảo:")
        print("    1. Dịch vụ MySQL đã được bật (chạy 'net start MySQL80' trong Administrator).")
        print("    2. Mật khẩu nhập đúng.")
        return

    sql_file = backend_dir / "scripts" / "init_db.sql"
    if not sql_file.exists():
        print(f"[!] Không tìm thấy file SQL: {sql_file}")
        conn.close()
        return

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Tách các câu lệnh theo dấu chấm phẩy
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    with conn.cursor() as cursor:
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except Exception as se:
                print(f"[!] Lỗi khi thực thi: {stmt[:50]}... -> {se}")

    conn.close()
    print("\n[+] ĐÃ KHỞI TẠO DATABASE 'traffic_accident' THÀNH CÔNG!")
    
    # Cập nhật lại file .env với mật khẩu vừa nhập
    env_file = backend_dir / ".env"
    new_db_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/traffic_accident?charset=utf8mb4"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(env_file, "w", encoding="utf-8") as f:
            found = False
            for line in lines:
                if line.startswith("DATABASE_URL="):
                    f.write(f"DATABASE_URL={new_db_url}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"DATABASE_URL={new_db_url}\n")
        print(f"[+] Đã tự động cập nhật chuỗi kết nối vào backend/.env")
    print("=========================================================\n")

if __name__ == "__main__":
    init_mysql_from_python()
