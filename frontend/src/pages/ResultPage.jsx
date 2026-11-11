import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Play,
  Pause,
  RotateCcw,
  Sliders,
  Car,
  ShieldAlert,
  ArrowLeft,
  Loader2,
  ExternalLink,
  ChevronRight,
  Maximize2,
} from 'lucide-react';
import { videoApi } from '../api';
import CanvasOverlay from '../components/CanvasOverlay';

export default function ResultPage() {
  const { id } = useParams();
  const videoRef = useRef(null);
  const timelineRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [videoData, setVideoData] = useState(null);
  const [resultData, setResultData] = useState(null);

  // Trạng thái phát video
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Toggles hiển thị
  const [showBoxes, setShowBoxes] = useState(true);
  const [showVehicles, setShowVehicles] = useState(true);

  // Cảnh báo đỏ nhấp nháy trên video
  const [isAccidentActive, setIsAccidentActive] = useState(false);

  // Tải thông tin video và kết quả JSON
  useEffect(() => {
    let isMounted = true;
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [detailRes, resultRes] = await Promise.all([
          videoApi.getVideoDetails(id),
          videoApi.getVideoResult(id),
        ]);

        if (isMounted) {
          setVideoData(detailRes.data);
          setResultData(resultRes.data);
          setDuration(detailRes.data.duration || resultRes.data.meta?.duration || 0);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Lỗi khi tải kết quả:', err);
          setError(
            err.response?.data?.detail || 'Không thể tải kết quả phân tích cho video này.'
          );
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      isMounted = false;
    };
  }, [id]);

  // Cập nhật currentTime khi video chạy
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || duration);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  // Tua đến thời điểm timestamp và tự động phát
  const seekTo = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, Math.min(seconds, duration));
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  // Tua trên thanh timeline khi bấm
  const handleTimelineClick = (e) => {
    if (!timelineRef.current || duration <= 0) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickRatio = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(clickRatio * duration);
  };

  // Định dạng mm:ss
  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
        <p className="text-slate-600 font-medium">Đang tải dữ liệu phân tích video...</p>
      </div>
    );
  }

  if (error || !videoData) {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-white rounded-2xl border border-slate-200 text-center space-y-4 shadow-sm">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-800">Không tìm thấy kết quả</h2>
        <p className="text-sm text-slate-500">{error || 'Video chưa hoàn tất phân tích hoặc đã bị xóa.'}</p>
        <Link
          to="/"
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 transition shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Quay lại trang phân tích</span>
        </Link>
      </div>
    );
  }

  const events = resultData?.events || videoData.events || [];
  const hasAccident = events.length > 0;
  const numEvents = events.length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Nút quay lại & Tiêu đề */}
      <div className="flex items-center justify-between">
        <Link
          to="/history"
          className="inline-flex items-center space-x-1.5 text-sm font-semibold text-slate-600 hover:text-blue-600 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Danh sách lịch sử</span>
        </Link>
        <span className="text-xs text-slate-400 font-mono">Video ID: #{videoData.id}</span>
      </div>

      {/* 1. BANNER KẾT LUẬN LỚN */}
      <div
        className={`p-6 rounded-2xl border shadow-sm transition-all duration-300 flex items-center justify-between ${
          hasAccident
            ? 'bg-gradient-to-r from-red-600 to-rose-700 text-white border-red-500 shadow-red-500/20'
            : 'bg-gradient-to-r from-emerald-600 to-teal-700 text-white border-emerald-500 shadow-emerald-500/20'
        }`}
      >
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-md flex items-center justify-center shrink-0 shadow-inner">
            {hasAccident ? (
              <AlertTriangle className="w-8 h-8 text-white animate-bounce" />
            ) : (
              <CheckCircle className="w-8 h-8 text-white" />
            )}
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight">
              {hasAccident
                ? `CẢNH BÁO: Phát hiện ${numEvents} vụ tai nạn giao thông!`
                : 'AN TOÀN: Không phát hiện tai nạn giao thông'}
            </h1>
            <p className="text-sm text-white/80 font-medium mt-0.5">
              Tên video: <span className="font-semibold">{videoData.filename}</span> • Thời lượng:{' '}
              {formatTime(duration)}
            </p>
          </div>
        </div>

        <div className="hidden sm:block text-right">
          <span className="inline-block px-3.5 py-1.5 rounded-full bg-white/20 backdrop-blur-md text-xs font-bold uppercase tracking-wider">
            {hasAccident ? `${numEvents} Sự kiện` : 'Bình thường'}
          </span>
        </div>
      </div>

      {/* 2. KHU VỰC VIDEO PLAYER VÀ CANVAS */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        {/* Video Screen Container */}
        <div className="relative bg-black aspect-video w-full flex items-center justify-center overflow-hidden select-none">
          {/* Cảnh báo nhấp nháy ĐỎ khi thời gian video nằm trong vụ tai nạn */}
          {isAccidentActive && (
            <div className="absolute top-4 left-4 z-20 flex items-center space-x-2.5 px-4 py-2 rounded-xl bg-red-600 text-white shadow-lg shadow-red-600/50 animate-blink border-2 border-white">
              <ShieldAlert className="w-5 h-5 text-white animate-pulse" />
              <span className="font-black text-sm tracking-wider uppercase">
                PHÁT HIỆN TAI NẠN
              </span>
            </div>
          )}

          {/* Video Gốc (giữ nguyên độ nét cao, phát qua HTTP Range stream) */}
          <video
            ref={videoRef}
            src={videoApi.getStreamUrl(videoData.id)}
            className="w-full h-full object-contain"
            playsInline
            onTimeUpdate={handleTimeUpdate}
            onLoadedMetadata={handleLoadedMetadata}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onClick={togglePlay}
          />

          {/* Canvas Overlay: vẽ Bounding Box đồng bộ frame */}
          <CanvasOverlay
            videoRef={videoRef}
            framesData={resultData?.frames || []}
            eventsData={events}
            showAccidents={showBoxes}
            showVehicles={showBoxes && showVehicles}
            onAccidentStateChange={(active) => setIsAccidentActive(active)}
          />
        </div>

        {/* 3. THANH TIMELINE DƯỚI VIDEO (ĐÁNH DẤU ĐOẠN ĐỎ TAI NẠN) */}
        <div className="px-6 pt-4 pb-2">
          <div
            ref={timelineRef}
            onClick={handleTimelineClick}
            className="relative w-full h-3 bg-slate-200 rounded-full cursor-pointer group hover:h-4 transition-all duration-150 overflow-hidden"
          >
            {/* Đánh dấu các khoảng thời gian xảy ra tai nạn màu đỏ */}
            {duration > 0 &&
              events.map((ev) => {
                const startPercent = (ev.start / duration) * 100;
                const widthPercent = Math.max(1, ((ev.end - ev.start) / duration) * 100);
                return (
                  <div
                    key={ev.id}
                    title={`Tai nạn #${ev.id}: ${formatTime(ev.start)} - ${formatTime(ev.end)}`}
                    className="absolute top-0 bottom-0 bg-red-500/90 hover:bg-red-600 transition-colors z-0"
                    style={{
                      left: `${startPercent}%`,
                      width: `${widthPercent}%`,
                    }}
                  />
                );
              })}

            {/* Thanh tiến trình hiện tại */}
            <div
              className="absolute top-0 bottom-0 bg-blue-600 rounded-full z-10 pointer-events-none"
              style={{
                width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%`,
              }}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 font-mono mt-1.5">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Bộ điều khiển & Công tắc Bật/Tắt Khung nhận diện */}
        <div className="px-6 py-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4 bg-slate-50/50">
          {/* Nút Play / Pause */}
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={togglePlay}
              className="w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center shadow-md shadow-blue-600/30 transition hover:scale-105"
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
            </button>

            <button
              type="button"
              onClick={() => seekTo(0)}
              className="p-2.5 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-200 transition"
              title="Phát lại từ đầu"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Công tắc Bật/Tắt Khung nhận diện */}
          <div className="flex items-center space-x-6">
            {/* Toggle Tai Nạn */}
            <label className="flex items-center space-x-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showBoxes}
                onChange={(e) => setShowBoxes(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 cursor-pointer"
              />
              <span className="text-sm font-semibold text-slate-700 flex items-center space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span>Khung tai nạn</span>
              </span>
            </label>

            {/* Toggle Phương Tiện (Xe) */}
            <label className="flex items-center space-x-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showVehicles}
                disabled={!showBoxes}
                onChange={(e) => setShowVehicles(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 cursor-pointer disabled:opacity-50"
              />
              <span
                className={`text-sm font-semibold flex items-center space-x-1.5 ${
                  !showBoxes ? 'text-slate-400' : 'text-slate-700'
                }`}
              >
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
                <span>Khung xe</span>
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* 4. PANEL DANH SÁCH SỰ KIỆN TAI NẠN */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-red-600" />
            <h2 className="text-base font-bold text-slate-800">
              Danh sách sự kiện tai nạn phát hiện ({numEvents})
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Bấm vào sự kiện để video tua đến thời điểm đó
          </span>
        </div>

        {events.length === 0 ? (
          <div className="py-8 text-center text-slate-400 space-y-2">
            <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
            <p className="text-sm font-medium">Không phát hiện sự cố tai nạn nào trong toàn bộ video.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {events.map((ev) => {
              const confPercent = Math.round((ev.max_confidence || 0) * 100);
              return (
                <div
                  key={ev.id}
                  onClick={() => seekTo(ev.start)}
                  className="group p-4 rounded-xl border border-slate-200/90 hover:border-red-400 bg-white hover:bg-red-50/30 transition-all duration-200 cursor-pointer flex space-x-4 shadow-sm hover:shadow-md"
                >
                  {/* Ảnh bằng chứng tại peak_time */}
                  <div className="relative w-32 h-20 rounded-lg overflow-hidden bg-slate-900 shrink-0 border border-slate-200 shadow-inner">
                    <img
                      src={videoApi.getEvidenceUrl(ev.evidence_image)}
                      alt={`Bằng chứng #${ev.id}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/75 text-[10px] font-mono text-white">
                      {formatTime(ev.peak_time)}
                    </div>
                  </div>

                  {/* Chi tiết sự kiện */}
                  <div className="flex-1 flex flex-col justify-between py-0.5">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-red-600 uppercase tracking-wide">
                          Sự kiện #{ev.id}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-bold text-xs">
                          {confPercent}% Tin cậy
                        </span>
                      </div>

                      <div className="mt-1 flex items-center space-x-1.5 text-xs text-slate-600 font-semibold">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        <span>
                          {formatTime(ev.start)} → {formatTime(ev.end)} (Đỉnh: {formatTime(ev.peak_time)})
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100 text-xs">
                      <div className="flex items-center space-x-1 text-slate-500 truncate max-w-[180px]">
                        <Car className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                        <span>
                          Xe liên quan:{' '}
                          {ev.track_ids && ev.track_ids.length > 0
                            ? ev.track_ids.map((tid) => `#${tid}`).join(', ')
                            : 'Không xác định'}
                        </span>
                      </div>

                      <span className="text-blue-600 font-bold flex items-center space-x-0.5 group-hover:translate-x-0.5 transition-transform">
                        <span>Tua tới</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
