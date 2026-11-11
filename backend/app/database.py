import sys
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config import DATABASE_URL

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    duration = Column(Float, default=0.0)
    status = Column(
        Enum("queued", "processing", "done", "error", name="video_status"),
        default="queued",
        nullable=False,
    )
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    num_events = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="video", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    peak_time = Column(Float, nullable=False)
    max_confidence = Column(Float, nullable=False)
    evidence_image = Column(String(500), nullable=False)

    video = relationship("Video", back_populates="events")

def get_engine_and_session():
    """
    Tạo kết nối Database với connection pool, pool_pre_ping=True
    và xử lý thông báo lỗi tiếng Việt nếu không kết nối được MySQL.
    """
    db_url = DATABASE_URL
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        # Thử kết nối kiểm tra
        with engine.connect() as conn:
            pass
        return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except OperationalError as e:
        err_str = str(e).lower()
        print("\n" + "!" * 70, file=sys.stderr)
        print("[LỖI KẾT NỐI DATABASE MYSQL]", file=sys.stderr)
        if "access denied" in err_str:
            print("=> Sai thông tin đăng nhập (USER hoặc PASSWORD) trong file .env!", file=sys.stderr)
            print("   Vui lòng kiểm tra lại cấu hình DATABASE_URL trong backend/.env", file=sys.stderr)
        elif "unknown database" in err_str:
            print("=> Database 'traffic_accident' chưa tồn tại! Đang tự động khởi tạo trên MySQL...", file=sys.stderr)
            try:
                import re
                from sqlalchemy import text
                # Cắt bỏ tên database để kết nối tới MySQL server gốc
                base_url = re.sub(r'/[a-zA-Z0-9_]+(\?.*)?$', r'/\1', db_url)
                temp_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
                with temp_engine.connect() as conn:
                    conn.execute(text("CREATE DATABASE IF NOT EXISTS traffic_accident CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                temp_engine.dispose()
                print("[+] Đã tự động tạo Database 'traffic_accident' thành công!", file=sys.stderr)
                
                # Thử kết nối lại sau khi đã tạo database
                engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600, echo=False)
                with engine.connect():
                    pass
                return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)
            except Exception as ce:
                print(f"[!] Không thể tự động tạo database: {ce}", file=sys.stderr)
        elif "can't connect" in err_str or "connection refused" in err_str or "2003" in err_str:
            print("=> Không thể kết nối tới dịch vụ MySQL!", file=sys.stderr)
            print("   Vui lòng kiểm tra dịch vụ MySQL Server đã được bật và đang lắng nghe cổng 3306 chưa.", file=sys.stderr)
        else:
            print(f"=> Lỗi MySQL: {e}", file=sys.stderr)
        print("!" * 70 + "\n", file=sys.stderr)

        # Hỗ trợ tự động fallback sang SQLite local cho môi trường dev/test khi chưa bật MySQL
        sqlite_fallback = "sqlite:///backend/storage/traffic_accident.db"
        print(f"[*] Đang tạm thời kích hoạt chế độ Fallback SQLite: {sqlite_fallback}", file=sys.stderr)
        fallback_engine = create_engine(sqlite_fallback, connect_args={"check_same_thread": False})
        return fallback_engine, sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)
    except Exception as e:
        print(f"[LỖI DATABASE KHÔNG XÁC ĐỊNH]: {e}", file=sys.stderr)
        sqlite_fallback = "sqlite:///backend/storage/traffic_accident.db"
        fallback_engine = create_engine(sqlite_fallback, connect_args={"check_same_thread": False})
        return fallback_engine, sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)

engine, SessionLocal = get_engine_and_session()

def init_db():
    """
    Tự động tạo các bảng trong database nếu chưa tồn tại.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("[Database] Đã khởi tạo schema bảng thành công.")
    except Exception as e:
        print(f"[Database Lỗi khởi tạo bảng]: {e}")

def get_db():
    """
    Dependency cung cấp database session cho FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
